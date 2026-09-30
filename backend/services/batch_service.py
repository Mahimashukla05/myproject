import json
import logging
import xml.etree.ElementTree as ET
from config.db import Database
from config.settings import Config
from models.parcel_model import ParcelModel
from models.audit_model import AuditModel
from models.user_model import UserModel
from services.parcel_service import ParcelService
from services.routing_service import RoutingService

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

        root_tag = root.tag.lower()
        if root_tag not in ["container", "parcels"]:
            raise ValueError("Invalid XML structure. Root element must be <Container> or <parcels>.")

        container_meta = None
        parcels_list = []

        if root_tag == "container":
            container_id = (root.findtext("Id") or root.findtext("id") or "").strip()
            shipping_date = (root.findtext("ShippingDate") or root.findtext("shippingDate") or root.findtext("Date") or "").strip()
            container_meta = {
                "containerId": container_id,
                "shippingDate": shipping_date
            }

            parcels_elem = root.find("parcels")
            if parcels_elem is None:
                parcels_elem = root.find("Parcels")

            parcel_nodes = []
            if parcels_elem is not None:
                parcel_nodes = parcels_elem.findall("Parcel") + parcels_elem.findall("parcel")
            else:
                parcel_nodes = root.findall("Parcel") + root.findall("parcel")

            for idx, elem in enumerate(parcel_nodes):
                pcl_id = (elem.findtext("Id") or elem.findtext("ParcelId") or elem.findtext("parcelId") or "").strip()
                if not pcl_id:
                    if container_id:
                        pcl_id = f"{container_id}-P{idx+1}"
                    else:
                        pcl_id = f"PCL-XML-{idx+1:03d}"

                rec_elem = elem.find("Receipient")
                if rec_elem is None:
                    rec_elem = elem.find("Recipient")
                if rec_elem is None:
                    rec_elem = elem.find("receipient")
                if rec_elem is None:
                    rec_elem = elem.find("recipient")

                rec_name = ""
                street = ""
                house_number = ""
                postal_code = ""
                city = ""

                if rec_elem is not None:
                    rec_name = (rec_elem.findtext("Name") or rec_elem.findtext("name") or "").strip()
                    addr_elem = rec_elem.find("Address")
                    if addr_elem is None:
                        addr_elem = rec_elem.find("address")
                    if addr_elem is not None:
                        street = (addr_elem.findtext("Street") or addr_elem.findtext("street") or "").strip()
                        house_number = (addr_elem.findtext("HouseNumber") or addr_elem.findtext("houseNumber") or "").strip()
                        postal_code = (addr_elem.findtext("PostalCode") or addr_elem.findtext("postalCode") or "").strip()
                        city = (addr_elem.findtext("City") or addr_elem.findtext("city") or "").strip()

                weight_raw = (elem.findtext("Weight") or elem.findtext("weight") or elem.findtext("weightKg") or "").strip()
                weight_val = None
                if weight_raw:
                    try:
                        weight_val = float(weight_raw)
                    except ValueError:
                        weight_val = weight_raw

                value_raw = (elem.findtext("Value") or elem.findtext("value") or elem.findtext("valueEur") or "").strip()
                value_val = None
                if value_raw:
                    try:
                        value_val = float(value_raw)
                    except ValueError:
                        value_val = value_raw

                sender_name = (elem.findtext("senderName") or "").strip() or None
                sender_contact = (elem.findtext("senderContact") or "").strip() or None
                receiver_name = (elem.findtext("receiverName") or rec_name or "").strip() or None
                receiver_contact = (elem.findtext("receiverContact") or "").strip() or None
                origin_val = (elem.findtext("origin") or "").strip() or None

                dest_constructed = city if city else "Destination"
                destination_val = (elem.findtext("destination") or dest_constructed or "").strip() or None

                item = {
                    "parcelId": pcl_id,
                    "senderName": sender_name,
                    "senderContact": sender_contact,
                    "receiverName": receiver_name,
                    "receiverContact": receiver_contact,
                    "origin": origin_val,
                    "destination": destination_val,
                    "weightKg": weight_val,
                    "valueEur": value_val,
                    "recipientName": rec_name or receiver_name,
                    "street": street,
                    "houseNumber": house_number,
                    "postalCode": postal_code,
                    "city": city
                }
                parcels_list.append(item)

        elif root_tag == "parcels":
            parcel_nodes = root.findall("parcel") + root.findall("Parcel")
            for elem in parcel_nodes:
                item = {}
                for child in elem:
                    tag = child.tag
                    text = (child.text or "").strip()
                    if tag in ["weightKg", "valueEur", "Weight", "Value"]:
                        try:
                            item[tag] = float(text)
                        except ValueError:
                            item[tag] = text
                    else:
                        item[tag] = text
                parcels_list.append(item)

        return parcels_list, container_meta

    @classmethod
    def parse_batch_file(cls, file_obj, filename, content_type):
        # 1. Filename & Extension Check
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[1].lower()

        if ext not in cls.ALLOWED_EXTENSIONS:
            return (None, None), ({"success": False, "error": f"Unsupported file extension '{ext}'. Only .json and .xml files are allowed."}, 400)

        # 2. MIME Type Check
        clean_mime = (content_type or "").split(";")[0].strip().lower()
        if clean_mime and clean_mime not in cls.ALLOWED_MIME_TYPES:
            return (None, None), ({"success": False, "error": f"Unsupported MIME type '{content_type}'."}, 400)

        # 3. Read Content & Check Size
        file_bytes = file_obj.read()
        if len(file_bytes) == 0:
            return (None, None), ({"success": False, "error": "Batch file is empty."}, 400)

        if len(file_bytes) > Config.MAX_BATCH_FILE_SIZE_BYTES:
            max_mb = Config.MAX_BATCH_FILE_SIZE_BYTES / (1024 * 1024)
            return (None, None), ({"success": False, "error": f"File size exceeds maximum allowed limit of {max_mb:.1f} MB."}, 413)

        # 4. Parse Content based on extension
        parcels_list = []
        container_meta = None
        if ext == ".json":
            try:
                data = json.loads(file_bytes.decode('utf-8'))
                if isinstance(data, dict) and "parcels" in data and isinstance(data["parcels"], list):
                    parcels_list = data["parcels"]
                elif isinstance(data, list):
                    parcels_list = data
                else:
                    return (None, None), ({"success": False, "error": "Invalid JSON batch structure. Expected a JSON object with a 'parcels' list."}, 400)
            except (json.JSONDecodeError, UnicodeDecodeError) as err:
                return (None, None), ({"success": False, "error": f"Malformed JSON file: {str(err)}"}, 400)

        elif ext == ".xml":
            try:
                parcels_list, container_meta = cls.safe_parse_xml(file_bytes)
            except ValueError as ve:
                err_msg = str(ve)
                if "Security Violation" in err_msg:
                    logger.warning(f"Security event: XXE / DTD attack payload blocked in XML batch upload.")
                    return (None, None), ({"success": False, "error": err_msg}, 400)
                return (None, None), ({"success": False, "error": err_msg}, 400)

        return (parcels_list, container_meta), None

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
        (parcels_list, container_meta), error_response = cls.parse_batch_file(file_obj, filename, content_type)
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

        # Helper to construct result payload item
        def make_result_item(index, parcel_id_str, item_dict, status, errors=None, error_type=None, department=None, parcel_status=None):
            res = {
                "index": index + 1,
                "parcelId": parcel_id_str,
                "recipientName": item_dict.get("recipientName") or item_dict.get("receiverName") or "",
                "street": item_dict.get("street") or "",
                "houseNumber": item_dict.get("houseNumber") or "",
                "postalCode": item_dict.get("postalCode") or "",
                "city": item_dict.get("city") or "",
                "destination": item_dict.get("destination") or "",
                "weightKg": item_dict.get("weightKg"),
                "valueEur": item_dict.get("valueEur"),
                "status": status
            }
            if item_dict.get("senderName") is not None:
                res["senderName"] = item_dict["senderName"]
            if item_dict.get("senderContact") is not None:
                res["senderContact"] = item_dict["senderContact"]
            if item_dict.get("receiverContact") is not None:
                res["receiverContact"] = item_dict["receiverContact"]
            if item_dict.get("origin") is not None:
                res["origin"] = item_dict["origin"]
            if department:
                res["department"] = department
            if parcel_status:
                res["parcelStatus"] = parcel_status
            if errors:
                res["errors"] = errors
            if error_type:
                res["errorType"] = error_type
            return res

        # 3. Row-by-Row Independent Parcel Validation & Processing
        for index, item in enumerate(parcels_list):
            if not isinstance(item, dict):
                failed += 1
                results.append(make_result_item(
                    index=index,
                    parcel_id_str=f"ROW-{index+1}",
                    item_dict={},
                    status="FAILED",
                    errors=["Invalid row structure. Parcel must be an object."],
                    error_type="VALIDATION"
                ))
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
            if file_type == ".json":
                required_fields = ["senderName", "senderContact", "receiverName", "receiverContact", "origin", "destination", "weightKg", "valueEur"]
            else:
                required_fields = ["receiverName", "destination", "weightKg", "valueEur"]

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
                results.append(make_result_item(
                    index=index,
                    parcel_id_str=parcel_id_str,
                    item_dict=item_clean,
                    status="FAILED",
                    errors=row_errors,
                    error_type="VALIDATION"
                ))
                continue

            # F. Database Existence Check & Unique Constraint Handling
            existing_doc = ParcelModel.find_by_parcel_id(parcel_id_str)
            if existing_doc:
                failed += 1
                results.append(make_result_item(
                    index=index,
                    parcel_id_str=parcel_id_str,
                    item_dict=item_clean,
                    status="FAILED",
                    errors=[f"Parcel ID '{parcel_id_str}' already exists in database."],
                    error_type="VALIDATION"
                ))
                continue

            try:
                # Create parcel record (initial state: RECEIVED)
                parcel_doc = ParcelModel.create_parcel({
                    "parcelId": parcel_id_str,
                    "senderName": item_clean.get("senderName"),
                    "senderContact": item_clean.get("senderContact"),
                    "receiverName": item_clean.get("receiverName"),
                    "receiverContact": item_clean.get("receiverContact"),
                    "origin": item_clean.get("origin"),
                    "destination": item_clean.get("destination"),
                    "weightKg": float(item_clean["weightKg"]),
                    "valueEur": float(item_clean["valueEur"]),
                    "submittedBy": user_id
                })

                # Route the newly created parcel using existing RoutingService
                route_res, route_code = RoutingService.route_parcel(parcel_id_str)
                if route_code != 200 or not route_res or not route_res.get("success"):
                    err_msg = route_res.get("error") if isinstance(route_res, dict) else "Routing evaluation failed"
                    failed += 1
                    results.append(make_result_item(
                        index=index,
                        parcel_id_str=parcel_id_str,
                        item_dict=item_clean,
                        status="FAILED",
                        errors=[err_msg],
                        error_type="TECHNICAL"
                    ))
                    continue

                routed_parcel = route_res.get("parcel") or {}
                successful += 1
                results.append(make_result_item(
                    index=index,
                    parcel_id_str=parcel_id_str,
                    item_dict=item_clean,
                    status="SUCCESS",
                    department=routed_parcel.get("department"),
                    parcel_status=routed_parcel.get("status")
                ))

            except Exception as ex:
                logger.error(f"Technical database error inserting parcel '{parcel_id_str}': {ex}")
                failed += 1
                if "duplicate key" in str(ex).lower() or "11000" in str(ex):
                    results.append(make_result_item(
                        index=index,
                        parcel_id_str=parcel_id_str,
                        item_dict=item_clean,
                        status="FAILED",
                        errors=[f"Parcel ID '{parcel_id_str}' already exists in database."],
                        error_type="VALIDATION"
                    ))
                else:
                    results.append(make_result_item(
                        index=index,
                        parcel_id_str=parcel_id_str,
                        item_dict=item_clean,
                        status="FAILED",
                        errors=["Technical database failure during insertion."],
                        error_type="TECHNICAL"
                    ))

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
        response_payload = {
            "success": True,
            "total": total,
            "successful": successful,
            "failed": failed,
            "results": results
        }
        if container_meta:
            if container_meta.get("containerId"):
                response_payload["containerId"] = container_meta["containerId"]
            if container_meta.get("shippingDate"):
                response_payload["shippingDate"] = container_meta["shippingDate"]

        return response_payload, 200
