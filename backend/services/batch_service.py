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
