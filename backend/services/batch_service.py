import json
import logging
import xml.etree.ElementTree as ET
from config.db import Database
from config.settings import Config
from models.parcel_model import ParcelModel
from models.audit_model import AuditModel
from models.user_model import UserModel
from services.parcel_service import ParcelService

logger = logging.getLogger("parcel_routing_app")

class BatchService:
    ALLOWED_EXTENSIONS = {".json", ".xml"}
    ALLOWED_MIME_TYPES = {
        "application/json", "text/json",
        "application/xml", "text/xml", "application/x-xml",
        "text/plain"
    }

    @classmethod
    def safe_parse_xml(cls, file_bytes):
        xml_str = file_bytes.decode('utf-8', errors='replace')
        upper_str = xml_str.upper()

        # XXE Protection: Forbid DOCTYPE and ENTITY declarations completely
        if "<!DOCTYPE" in upper_str or "<!ENTITY" in upper_str:
            raise ValueError("Security Violation: XML containing DOCTYPE or ENTITY declarations is forbidden.")

        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as pe:
            raise ValueError(f"Malformed XML syntax: {str(pe)}")

        if root.tag.lower() != "parcels":
            raise ValueError("Invalid XML structure. Root element must be <parcels>.")

        parcels_list = []
        for elem in root.findall("parcel"):
            item = {}
            for child in elem:
                tag = child.tag
                text = (child.text or "").strip()
                if tag in ["weightKg", "valueEur"]:
                    try:
                        item[tag] = float(text)
                    except ValueError:
                        item[tag] = text
                else:
                    item[tag] = text
            parcels_list.append(item)

        return parcels_list

    @classmethod
    def parse_batch_file(cls, file_obj, filename, content_type):
        # 1. Filename & Extension Check
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[1].lower()

        if ext not in cls.ALLOWED_EXTENSIONS:
            return None, ({"success": False, "error": f"Unsupported file extension '{ext}'. Only .json and .xml files are allowed."}, 400)

        # 2. MIME Type Check
        clean_mime = (content_type or "").split(";")[0].strip().lower()
        if clean_mime and clean_mime not in cls.ALLOWED_MIME_TYPES:
            return None, ({"success": False, "error": f"Unsupported MIME type '{content_type}'."}, 400)

        # 3. Read Content & Check Size
        file_bytes = file_obj.read()
        if len(file_bytes) == 0:
            return None, ({"success": False, "error": "Batch file is empty."}, 400)

        if len(file_bytes) > Config.MAX_BATCH_FILE_SIZE_BYTES:
            max_mb = Config.MAX_BATCH_FILE_SIZE_BYTES / (1024 * 1024)
            return None, ({"success": False, "error": f"File size exceeds maximum allowed limit of {max_mb:.1f} MB."}, 413)

        # 4. Parse Content based on extension
        parcels_list = []
        if ext == ".json":
            try:
                data = json.loads(file_bytes.decode('utf-8'))
                if isinstance(data, dict) and "parcels" in data and isinstance(data["parcels"], list):
                    parcels_list = data["parcels"]
                elif isinstance(data, list):
                    parcels_list = data
                else:
                    return None, ({"success": False, "error": "Invalid JSON batch structure. Expected a JSON object with a 'parcels' list."}, 400)
            except (json.JSONDecodeError, UnicodeDecodeError) as err:
                return None, ({"success": False, "error": f"Malformed JSON file: {str(err)}"}, 400)

        elif ext == ".xml":
            try:
                parcels_list = cls.safe_parse_xml(file_bytes)
            except ValueError as ve:
                err_msg = str(ve)
                if "Security Violation" in err_msg:
                    logger.warning(f"Security event: XXE / DTD attack payload blocked in XML batch upload.")
                    return None, ({"success": False, "error": err_msg}, 400)
                return None, ({"success": False, "error": err_msg}, 400)

        return parcels_list, None

    @classmethod
    def process_batch(cls, file_obj, filename, content_type, user_id, user_info=None):
        # Determine actor details for audit logging
        actor_id = str(user_id)
        actor_username = "operator"
        actor_role = "operator"

        if user_info and isinstance(user_info, dict):
            actor_id = str(user_info.get("_id") or user_info.get("id") or user_id)
            actor_username = user_info.get("username", "operator")
            actor_role = user_info.get("role", "operator")
        else:
            user_doc = UserModel.find_by_id(user_id)
            if user_doc:
                actor_username = user_doc.get("username", "operator")
                actor_role = user_doc.get("role", "operator")

        ext = ""
        if filename and "." in filename:
            ext = "." + filename.rsplit(".", 1)[1].lower()
        file_type = ext if ext else "UNKNOWN"

        # 1. Database Liveness Check
        db = Database.get_db()
        if db is None:
            logger.error("Batch processing failed: Database is currently unavailable.")
            return {
                "success": False,
                "error": "Database is currently unavailable. Please try again later.",
                "errorType": "TECHNICAL"
            }, 503

        # 2. File Parsing & Pre-validation
        parcels_list, error_response = cls.parse_batch_file(file_obj, filename, content_type)
        if error_response:
            AuditModel.log_event(
                actor_id=actor_id,
                actor_username=actor_username,
                actor_role=actor_role,
                action="BATCH_UPLOAD",
                parcel_id=None,
                details={
                    "fileType": file_type,
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "outcome": "FORMAT_ERROR"
                }
            )
            return error_response[0], error_response[1]

        if not parcels_list or len(parcels_list) == 0:
            AuditModel.log_event(
                actor_id=actor_id,
                actor_username=actor_username,
                actor_role=actor_role,
                action="BATCH_UPLOAD",
                parcel_id=None,
                details={
                    "fileType": file_type,
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "outcome": "FORMAT_ERROR"
                }
            )
            return {"success": False, "error": "Batch file contains no parcel records."}, 400

        total = len(parcels_list)
        successful = 0
        failed = 0
        results = []
        seen_parcel_ids = set()

        # 3. Row-by-Row Independent Parcel Validation & Processing
        for index, item in enumerate(parcels_list):
            if not isinstance(item, dict):
                failed += 1
                results.append({
                    "parcelId": f"ROW-{index+1}",
                    "status": "FAILED",
                    "errors": ["Invalid row structure. Parcel must be an object."],
                    "errorType": "VALIDATION"
                })
                continue

            # Strip client-controlled system metadata fields if provided
            item_clean = {k: v for k, v in item.items() if k not in [
                "department", "insuranceRequired", "insuranceStatus", "status",
                "submittedBy", "submittedAt", "updatedAt", "failureReason"
            ]}

            row_errors = []

            # A. Check parcelId requirement
            parcel_id = item_clean.get("parcelId")
            if parcel_id is None or (isinstance(parcel_id, str) and not parcel_id.strip()):
                row_errors.append("Field 'parcelId' is required and cannot be empty.")
                parcel_id_str = f"ROW-{index+1}"
            else:
                parcel_id_str = str(parcel_id).strip()

            # B. Check missing required fields
            required_fields = ["senderName", "senderContact", "receiverName", "receiverContact", "origin", "destination", "weightKg", "valueEur"]
            missing = [f for f in required_fields if f not in item_clean or item_clean[f] is None or (isinstance(item_clean[f], str) and not item_clean[f].strip())]
            if missing:
                row_errors.append(f"Missing required fields: {', '.join(missing)}")

            # C. Validate string fields
            for fname in ["senderName", "senderContact", "receiverName", "receiverContact", "origin", "destination"]:
                if fname in item_clean and item_clean[fname] is not None:
                    err = ParcelService.validate_string_field(item_clean[fname], fname)
                    if err:
                        row_errors.append(err)

            # D. Validate numeric fields
            if "weightKg" in item_clean and item_clean["weightKg"] is not None:
                err = ParcelService.validate_numeric_field(item_clean["weightKg"], "weightKg", min_value=0.0, allow_zero=False)
                if err:
                    row_errors.append(err)

            if "valueEur" in item_clean and item_clean["valueEur"] is not None:
                err = ParcelService.validate_numeric_field(item_clean["valueEur"], "valueEur", min_value=0.0, allow_zero=True)
                if err:
                    row_errors.append(err)

            # E. Intra-batch duplicate parcelId check
            if parcel_id_str != f"ROW-{index+1}" and parcel_id_str in seen_parcel_ids:
                row_errors.append(f"Duplicate parcelId '{parcel_id_str}' inside batch.")
            elif parcel_id_str != f"ROW-{index+1}":
                seen_parcel_ids.add(parcel_id_str)

            # If validation errors occurred, mark row as failed
            if row_errors:
                failed += 1
                results.append({
                    "parcelId": parcel_id_str,
                    "status": "FAILED",
                    "errors": row_errors,
                    "errorType": "VALIDATION"
                })
                continue

            # F. Database Existence Check & Unique Constraint Handling
            existing_doc = ParcelModel.find_by_parcel_id(parcel_id_str)
            if existing_doc:
                failed += 1
                results.append({
                    "parcelId": parcel_id_str,
                    "status": "FAILED",
                    "errors": [f"Parcel ID '{parcel_id_str}' already exists in database."],
                    "errorType": "VALIDATION"
                })
                continue

            try:
                # Create parcel record (remains in default RECEIVED status)
                parcel_doc = ParcelModel.create_parcel({
                    "parcelId": parcel_id_str,
                    "senderName": str(item_clean["senderName"]).strip(),
                    "senderContact": str(item_clean["senderContact"]).strip(),
                    "receiverName": str(item_clean["receiverName"]).strip(),
                    "receiverContact": str(item_clean["receiverContact"]).strip(),
                    "origin": str(item_clean["origin"]).strip(),
                    "destination": str(item_clean["destination"]).strip(),
                    "weightKg": float(item_clean["weightKg"]),
                    "valueEur": float(item_clean["valueEur"]),
                    "submittedBy": user_id
                })

                successful += 1
                results.append({
                    "parcelId": parcel_id_str,
                    "status": "SUCCESS"
                })

            except Exception as ex:
                logger.error(f"Technical database error inserting parcel '{parcel_id_str}': {ex}")
                failed += 1
                if "duplicate key" in str(ex).lower() or "11000" in str(ex):
                    results.append({
                        "parcelId": parcel_id_str,
                        "status": "FAILED",
                        "errors": [f"Parcel ID '{parcel_id_str}' already exists in database."],
                        "errorType": "VALIDATION"
                    })
                else:
                    results.append({
                        "parcelId": parcel_id_str,
                        "status": "FAILED",
                        "errors": ["Technical database failure during insertion."],
                        "errorType": "TECHNICAL"
                    })

        # Determine batch outcome
        if failed == 0 and total > 0:
            outcome = "SUCCESS"
        elif successful > 0 and failed > 0:
            outcome = "PARTIAL_FAILURE"
        else:
            outcome = "FAILURE"

        AuditModel.log_event(
            actor_id=actor_id,
            actor_username=actor_username,
            actor_role=actor_role,
            action="BATCH_UPLOAD",
            parcel_id=None,
            details={
                "fileType": file_type,
                "total": total,
                "successful": successful,
                "failed": failed,
                "outcome": outcome
            }
        )

        logger.info(f"Batch processed by user '{user_id}': Total={total}, Successful={successful}, Failed={failed}, Outcome={outcome}")
        return {
            "success": True,
            "total": total,
            "successful": successful,
            "failed": failed,
            "results": results
        }, 200
