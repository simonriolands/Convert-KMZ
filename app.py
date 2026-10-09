import streamlit as st
import zipfile
import os
import shutil
import xml.etree.ElementTree as ET
import copy
import tempfile
import re

def hex_to_kml_color(hex_color):
    if not hex_color or str(hex_color).strip() == "":
        return "" 
    hex_color = hex_color.replace("#", "")
    if len(hex_color) == 6:
        r = hex_color[0:2]
        g = hex_color[2:4]
        b = hex_color[4:6]
        return f"ff{b}{g}{r}".lower()
    return hex_color

def proses_kmz(input_path, output_path, extract_dir, jenis_kmz, format_tahapan, list_rename):
    # ==========================================
    # 1. KONFIGURASI FOLDER STANDAR BERDASARKAN TIPE
    # ==========================================
    if jenis_kmz == "Cluster":
        daftar_folder_standar = [
            "BOUNDARY FAT", "FAT", "HP COVER", "HP UNCOVER", 
            "EXISTING POLE EMR 7-2.5", "EXISTING POLE EMR 7-3", "EXISTING POLE EMR 7-4", "EXISTING POLE EMR 9-4", 
            "EXISTING POLE PARTNER 7-4", "EXISTING POLE PARTNER 9-4", 
            "NEW POLE 7-2.5", "NEW POLE 7-3", "NEW POLE 7-4", "NEW POLE 9-4", 
            "DISTRIBUTION CABLE", "SLACK HANGER", "SLING WIRE"
        ]
    elif jenis_kmz == "Subfeeder":
        daftar_folder_standar = [
            "JOINT CLOSURE", 
            "EXISTING POLE EMR 7-2.5", "EXISTING POLE EMR 7-3", "EXISTING POLE EMR 7-4", "EXISTING POLE EMR 7-5", 
            "EXISTING POLE EMR 9-5", "EXISTING POLE EMR 9-4", 
            "EXISTING POLE PARTNER 7-4", "EXISTING POLE PARTNER 9-4", 
            "NEW POLE 7-5", "NEW POLE 9-5", "NEW POLE 7-4", "NEW POLE 9-4", 
            "CABLE", "SLACK HANGER"
        ]
    elif jenis_kmz == "Feeder":
        daftar_folder_standar = [
            "OLT", "CABLE", 
            "EXISTING POLE EMR 7-3", "EXISTING POLE EMR 7-4", "EXISTING POLE EMR 7-5", 
            "EXISTING POLE EMR 9-5", "EXISTING POLE EMR 9-4", 
            "EXISTING POLE PARTNER 7-4", "EXISTING POLE PARTNER 9-4", 
            "NEW POLE 7-5", "NEW POLE 7-4", "NEW POLE 9-5", "NEW POLE 9-4", 
            "JOINT CLOSURE", "SLACK HANGER"
        ]

    folder_existing_pole = [
        "EXISTING POLE EMR 7-2.5", "EXISTING POLE EMR 7-3", "EXISTING POLE EMR 7-4", "EXISTING POLE EMR 7-5",
        "EXISTING POLE EMR 9-5", "EXISTING POLE EMR 9-4", 
        "EXISTING POLE PARTNER 7-4", "EXISTING POLE PARTNER 9-4"
    ]

    target_hapus_spasi = [
        "BOUNDARY FAT", "EXISTING POLE EMR 7-2.5", "EXISTING POLE EMR 7-3", 
        "EXISTING POLE EMR 7-4", "EXISTING POLE EMR 7-5", "EXISTING POLE EMR 9-4", 
        "EXISTING POLE EMR 9-5", "EXISTING POLE PARTNER 7-4", "EXISTING POLE PARTNER 9-4", 
        "FAT", "FDT", "NEW POLE 7-2.5", "NEW POLE 7-3", "NEW POLE 7-4", 
        "NEW POLE 7-5", "NEW POLE 9-4", "NEW POLE 9-5", "SLACK HANGER"
    ]

    with zipfile.ZipFile(input_path, 'r') as kmz:
        kmz.extractall(extract_dir)

    file_kml = None
    for file in os.listdir(extract_dir):
        if file.endswith(".kml"):
            file_kml = os.path.join(extract_dir, file)
            break

    if not file_kml:
        raise Exception("File KML tidak ditemukan di dalam KMZ.")

    with open(file_kml, 'r', encoding='utf-8') as f:
        kml_data = f.read()

    namespaces_wajib = [
        ('xmlns:gx', '"http://www.google.com/kml/ext/2.2"'),
        ('xmlns:kml', '"http://www.opengis.net/kml/2.2"'),
        ('xmlns:atom', '"http://www.w3.org/2005/Atom"'),
        ('xmlns:xal', '"urn:oasis:names:tc:ciq:xsdschema:xAL:2.0"'),
        ('xmlns:xsi', '"http://www.w3.org/2001/XMLSchema-instance"')
    ]

    kml_tag_match = re.search(r'<kml[^>]*>', kml_data)
    if kml_tag_match:
        kml_tag = kml_tag_match.group(0)
        new_kml_tag = kml_tag
        if '<kml>' in new_kml_tag:
            new_kml_tag = new_kml_tag.replace('<kml>', '<kml >')
        
        for ns_prefix, url in namespaces_wajib:
            if ns_prefix not in new_kml_tag:
                new_kml_tag = new_kml_tag.replace('<kml ', f'<kml {ns_prefix}={url} ')
        
        if new_kml_tag != kml_tag:
            kml_data = kml_data.replace(kml_tag, new_kml_tag)
            with open(file_kml, 'w', encoding='utf-8') as f:
                f.write(kml_data)

    namespace_kml = "http://www.opengis.net/kml/2.2"
    namespace_gx = "http://www.google.com/kml/ext/2.2"
    ET.register_namespace('', namespace_kml)
    ET.register_namespace('gx', namespace_gx)
    ET.register_namespace('atom', "http://www.w3.org/2005/Atom")
    ns = {'kml': namespace_kml, 'gx': namespace_gx}
    
    tree = ET.parse(file_kml)
    root = tree.getroot()

    document_elem = root.find('kml:Document', ns)
    if document_elem is None:
        document_elem = root.find('Document')
    if document_elem is None:
        document_elem = ET.SubElement(root, '{%s}Document' % namespace_kml)

    # ==========================================
    # 2. DEKLARASI GAYA KESELURUHAN (SHARED STYLES)
    # ==========================================
    def buat_shared_style(style_id, warna_titik, warna_teks, ukuran, icon_url, hide_balloon=True):
        style_elem = ET.SubElement(document_elem, '{%s}Style' % namespace_kml, attrib={f'{{{namespace_kml}}}id': style_id})
        if hide_balloon:
            b_style = ET.SubElement(style_elem, '{%s}BalloonStyle' % namespace_kml)
            ET.SubElement(b_style, '{%s}displayMode' % namespace_kml).text = "hide"
            
        icon_style = ET.SubElement(style_elem, '{%s}IconStyle' % namespace_kml)
        if warna_titik:
            ET.SubElement(icon_style, '{%s}color' % namespace_kml).text = hex_to_kml_color(warna_titik)
        ET.SubElement(icon_style, '{%s}scale' % namespace_kml).text = ukuran
        icon = ET.SubElement(icon_style, '{%s}Icon' % namespace_kml)
        ET.SubElement(icon, '{%s}href' % namespace_kml).text = icon_url
        
        label_style = ET.SubElement(style_elem, '{%s}LabelStyle' % namespace_kml)
        if warna_teks:
            ET.SubElement(label_style, '{%s}color' % namespace_kml).text = hex_to_kml_color(warna_teks)
        ET.SubElement(label_style, '{%s}scale' % namespace_kml).text = ukuran

    def buat_shared_line_style(style_id, warna_garis, ketebalan, hide_balloon=True):
        style_elem = ET.SubElement(document_elem, '{%s}Style' % namespace_kml, attrib={f'{{{namespace_kml}}}id': style_id})
        if hide_balloon:
            b_style = ET.SubElement(style_elem, '{%s}BalloonStyle' % namespace_kml)
            ET.SubElement(b_style, '{%s}displayMode' % namespace_kml).text = "hide"
            
        line_style = ET.SubElement(style_elem, '{%s}LineStyle' % namespace_kml)
        if warna_garis:
            ET.SubElement(line_style, '{%s}color' % namespace_kml).text = hex_to_kml_color(warna_garis)
        ET.SubElement(line_style, '{%s}width' % namespace_kml).text = ketebalan

    # Styles untuk Cluster
    buat_shared_style("shared_style_FAT", "#FFFF00", "#FFFF00", "0.8", "http://maps.google.com/mapfiles/kml/shapes/triangle.png", hide_balloon=True)
    buat_shared_style("shared_style_HP_COVER", "#00FF00", "#00FF00", "0.8", "http://maps.google.com/mapfiles/kml/shapes/homegardenbusiness.png", hide_balloon=True)
    buat_shared_style("shared_style_HP_UNCOVER", "#FF0000", "#FF0000", "0.8", "http://maps.google.com/mapfiles/kml/shapes/homegardenbusiness.png", hide_balloon=True)
    
    # Styles Titik Pole & Node
    buat_shared_style("style_olt", "#FFFFFF", "#FFFFFF", "0.8", "http://maps.google.com/mapfiles/kml/shapes/ranger_station.png", hide_balloon=True)
    buat_shared_style("style_jc_48", "#AA00FF", "#AA00FF", "0.8", "http://maps.google.com/mapfiles/kml/shapes/forbidden.png", hide_balloon=True)
    buat_shared_style("style_jc_144", "#FFFF00", "#FFFF00", "0.8", "http://maps.google.com/mapfiles/kml/shapes/forbidden.png", hide_balloon=True)
    buat_shared_style("style_jc_288", "#FFAA00", "#FFAA00", "0.8", "http://maps.google.com/mapfiles/kml/shapes/forbidden.png", hide_balloon=True)
    buat_shared_style("style_jc_ext", "#FFFFFF", "#FFFFFF", "0.8", "http://maps.google.com/mapfiles/kml/shapes/forbidden.png", hide_balloon=True)
    
    buat_shared_style("style_slack_ext", "#FFFFFF", "#FFFFFF", "0.8", "http://maps.google.com/mapfiles/kml/shapes/target.png", hide_balloon=True)
    buat_shared_style("style_slack_new", "#FF0000", "#FF0000", "0.8", "http://maps.google.com/mapfiles/kml/shapes/target.png", hide_balloon=True)
    buat_shared_style("shared_style_slack_hanger_copy", "#FFFFFF", "#FFFFFF", "0.8", "http://maps.google.com/mapfiles/kml/shapes/target.png", hide_balloon=True)
    
    buat_shared_style("style_pole_ext", "#FFFFFF", "#FFFFFF", "0.8", "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png", hide_balloon=True)
    buat_shared_style("style_pole_new_green", "#00FF00", "#00FF00", "0.8", "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png", hide_balloon=True)
    buat_shared_style("style_pole_new_red", "#FF0000", "#FF0000", "0.8", "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png", hide_balloon=True)
    buat_shared_style("style_pole_new_purple", "#AA00FF", "#AA00FF", "0.8", "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png", hide_balloon=True)
    buat_shared_style("style_pole_new_cyan", "#00FFFF", "#00FFFF", "0.8", "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png", hide_balloon=True)

    # Styles Kabel dan Jalur (Width 3.0)
    buat_shared_line_style("style_cable_24", "#00FF00", "3.0", hide_balloon=False)
    buat_shared_line_style("style_cable_36", "#FF00FF", "3.0", hide_balloon=False)
    buat_shared_line_style("style_cable_48", "#AA00FF", "3.0", hide_balloon=False)
    buat_shared_line_style("style_cable_96", "#FF0000", "3.0", hide_balloon=False)
    buat_shared_line_style("style_cable_144", "#FFFF00", "3.0", hide_balloon=False)
    buat_shared_line_style("style_cable_288", "#FFAA00", "3.0", hide_balloon=False)
    buat_shared_line_style("shared_style_sling_wire", "#00FFFF", "3.0", hide_balloon=False)

    # Styles FDT
    cross_hair_icon = "http://maps.google.com/mapfiles/kml/shapes/cross-hairs.png"
    buat_shared_style("shared_style_fdt_96c", "#FF0000", "#FF0000", "0.8", cross_hair_icon, hide_balloon=False)
    buat_shared_style("shared_style_fdt_72c", "#550000", "#550000", "0.8", cross_hair_icon, hide_balloon=False)
    buat_shared_style("shared_style_fdt_48c", "#AA00FF", "#AA00FF", "0.8", cross_hair_icon, hide_balloon=False)
    buat_shared_style("shared_style_fdt_sharing", "#FFFFFF", "#FFFFFF", "0.8", cross_hair_icon, hide_balloon=False)

    parent_map = {c: p for p in root.iter() for c in p}

    def get_kategori(folder_elem):
        curr = folder_elem
        valid_folders = set([
            "BOUNDARY FAT", "FAT", "FDT", "HP COVER", "HP UNCOVER", 
            "EXISTING POLE EMR 7-2.5", "EXISTING POLE EMR 7-3", "EXISTING POLE EMR 7-4", "EXISTING POLE EMR 7-5", 
            "EXISTING POLE EMR 9-4", "EXISTING POLE EMR 9-5", "EXISTING POLE PARTNER 7-4", "EXISTING POLE PARTNER 9-4", 
            "NEW POLE 7-2.5", "NEW POLE 7-3", "NEW POLE 7-4", "NEW POLE 7-5", "NEW POLE 9-4", "NEW POLE 9-5", 
            "DISTRIBUTION CABLE", "CABLE", "SLACK HANGER", "SLING WIRE", "OLT", "JOINT CLOSURE"
        ])
        while curr is not None:
            if curr.tag == f'{{{namespace_kml}}}Folder' or curr.tag == 'Folder':
                nama_elem = curr.find('kml:name', ns)
                if nama_elem is None: nama_elem = curr.find('name')
                if nama_elem is not None and nama_elem.text:
                    nama = nama_elem.text.strip().upper()
                    if nama in valid_folders or "BOUNDARY" in nama or "CABLE" in nama:
                        return nama
            curr = parent_map.get(curr)
        
        nama_elem = folder_elem.find('kml:name', ns)
        if nama_elem is None: nama_elem = folder_elem.find('name')
        return nama_elem.text.strip().upper() if (nama_elem is not None and nama_elem.text) else ""

    def terapkan_rename(teks):
        if not teks:
            return teks
        for cari, ganti in list_rename:
            if cari and cari.strip():
                teks = teks.replace(cari.strip(), ganti.strip() if ganti else "")
        return teks

    # ==========================================
    # 3. PENGHAPUSAN FOLDER ILEGAL & PENYUSUNAN STANDAR
    # ==========================================
    for folder in root.findall('.//kml:Folder', ns) + root.findall('.//Folder'):
        nama_folder_elem = folder.find('kml:name', ns)
        if nama_folder_elem is None: nama_folder_elem = folder.find('name')
        
        if nama_folder_elem is not None and nama_folder_elem.text:
            nama_folder = nama_folder_elem.text.strip()
            nama_folder = terapkan_rename(nama_folder)
            nama_folder_elem.text = nama_folder
            
            if nama_folder.upper().startswith("LINE"):
                semua_elemen_anak = list(folder)
                sub_folders_dict = {}
                elemen_lainnya = []
                
                for anak in semua_elemen_anak:
                    tag_name = anak.tag.split('}')[-1]
                    if tag_name == 'Folder':
                        sub_nama_elem = anak.find('kml:name', ns)
                        if sub_nama_elem is None: sub_nama_elem = anak.find('name')
                        sub_nama = sub_nama_elem.text.strip().upper() if (sub_nama_elem is not None and sub_nama_elem.text) else ""
                        sub_folders_dict[sub_nama] = anak
                    else:
                        elemen_lainnya.append(anak)
                
                for nama_target in daftar_folder_standar:
                    if nama_target not in sub_folders_dict:
                        folder_baru = ET.Element(f'{{{namespace_kml}}}Folder')
                        nama_elemen_baru = ET.SubElement(folder_baru, f'{{{namespace_kml}}}name')
                        nama_elemen_baru.text = nama_target
                        sub_folders_dict[nama_target] = folder_baru
                
                for anak in semua_elemen_anak:
                    folder.remove(anak)
                for elemen in elemen_lainnya:
                    folder.append(elemen)
                for nama_target in daftar_folder_standar:
                    if nama_target in sub_folders_dict:
                        folder.append(sub_folders_dict[nama_target])

    # Bersihkan style internal di level folder
    for folder_elem in root.findall('.//kml:Folder', ns) + root.findall('.//Folder'):
        nama_f_elem = folder_elem.find('kml:name', ns)
        if nama_f_elem is None: nama_f_elem = folder_elem.find('name')
        nama_f = nama_f_elem.text.strip().upper() if (nama_f_elem is not None and nama_f_elem.text) else ""
        if "BOUNDARY" not in nama_f and "CABLE" not in nama_f and "FDT" not in nama_f:
            for f_style in list(folder_elem.findall('kml:Style', ns) + folder_elem.findall('Style') + folder_elem.findall('kml:StyleMap', ns) + folder_elem.findall('StyleMap')):
                folder_elem.remove(f_style)

    # ==========================================
    # 4. APLIKASI GAYA, HAPUS SPASI, MULTI RENAME & CABLE FORMATTER
    # ==========================================
    for folder in root.findall('.//kml:Folder', ns) + root.findall('.//Folder'):
        kategori_efektif = get_kategori(folder)
        if not kategori_efektif:
            continue

        is_kecuali = ("FDT" in kategori_efektif) or ("CABLE" in kategori_efektif) or ("BOUNDARY" in kategori_efektif)
        
        for placemark in folder.findall('./kml:Placemark', ns) + folder.findall('./Placemark'):
            if not is_kecuali:
                tags_to_purge = [
                    'kml:description', 'kml:Snippet', 'gx:balloonVisibility', 'description', 'Snippet', 'balloonVisibility',
                    'kml:TimeStamp', 'kml:TimeSpan', 'TimeStamp', 'TimeSpan', 'kml:ExtendedData', 'ExtendedData'
                ]
                for tag in tags_to_purge:
                    elem_to_remove = placemark.find(tag, ns)
                    if elem_to_remove is not None:
                        placemark.remove(elem_to_remove)

                for tag_to_remove in ['kml:styleUrl', 'kml:Style', 'kml:StyleMap', 'styleUrl', 'Style', 'StyleMap']:
                    for elem_to_remove in list(placemark.findall(tag_to_remove, ns) + placemark.findall(tag_to_remove)):
                        placemark.remove(elem_to_remove)

            nama_placemark_elem = placemark.find('kml:name', ns)
            if nama_placemark_elem is None: 
                nama_placemark_elem = placemark.find('name')
            
            if nama_placemark_elem is not None and nama_placemark_elem.text:
                teks_nama = nama_placemark_elem.text.strip()
                teks_nama = terapkan_rename(teks_nama)
                
                if kategori_efektif in target_hapus_spasi:
                    teks_nama = teks_nama.replace(" ", "")
                
                nama_placemark_elem.text = teks_nama

            nama_placemark = nama_placemark_elem.text.upper() if nama_placemark_elem is not None and nama_placemark_elem.text else ""
            style_ref = None

            # Standarisasi Placemark Kabel
            if "CABLE" in kategori_efektif:
                if any(x in nama_placemark for x in ["288C", "288 CORE", "288"]):
                    if nama_placemark_elem is not None:
                        nama_placemark_elem.text = "FO 288C/24T"
                    style_ref = "#style_cable_288"
                elif any(x in nama_placemark for x in ["144C", "144 CORE", "144"]):
                    if nama_placemark_elem is not None:
                        nama_placemark_elem.text = "FO 144C/12T"
                    style_ref = "#style_cable_144"
                elif any(x in nama_placemark for x in ["96C", "96 CORE", "96"]):
                    if nama_placemark_elem is not None:
                        nama_placemark_elem.text = "FO 96C/8T"
                    style_ref = "#style_cable_96"
                elif any(x in nama_placemark for x in ["48C", "48 CORE", "48"]):
                    if nama_placemark_elem is not None:
                        nama_placemark_elem.text = "FO 48C/4T"
                    style_ref = "#style_cable_48"
                elif any(x in nama_placemark for x in ["36C", "36 CORE", "36"]):
                    if nama_placemark_elem is not None:
                        nama_placemark_elem.text = "FO 36C/3T"
                    style_ref = "#style_cable_36"
                elif any(x in nama_placemark for x in ["24C", "24 CORE", "24"]):
                    if nama_placemark_elem is not None:
                        nama_placemark_elem.text = "FO 24C/2T"
                    style_ref = "#style_cable_24"
                else:
                    style_ref = "#style_cable_24"

            elif kategori_efektif in folder_existing_pole:
                if nama_placemark_elem is not None and nama_placemark_elem.text:
                    if "EXT." not in nama_placemark:
                        nama_placemark_elem.text = "EXT." + nama_placemark_elem.text.strip()
                style_ref = "#style_pole_ext"

            elif kategori_efektif.startswith("NEW POLE"):
                if jenis_kmz == "Cluster":
                    if "7-2.5" in kategori_efektif: style_ref = "#style_pole_new_purple"
                    elif "7-3" in kategori_efektif: style_ref = "#style_pole_new_cyan"
                    elif "7-4" in kategori_efektif: style_ref = "#style_pole_new_green"
                    elif "9-4" in kategori_efektif: style_ref = "#style_pole_new_red"
                elif jenis_kmz == "Subfeeder":
                    if "7-5" in kategori_efektif or "9-5" in kategori_efektif or "7-4" in kategori_efektif: 
                        style_ref = "#style_pole_new_green" 
                    elif "9-4" in kategori_efektif: 
                        style_ref = "#style_pole_new_red"    
                elif jenis_kmz == "Feeder":
                    if "7-5" in kategori_efektif or "7-4" in kategori_efektif: style_ref = "#style_pole_new_green"
                    elif "9-5" in kategori_efektif or "9-4" in kategori_efektif: style_ref = "#style_pole_new_red"

            elif kategori_efektif == "JOINT CLOSURE":
                if "48" in nama_placemark: style_ref = "#style_jc_48"
                elif "144" in nama_placemark: style_ref = "#style_jc_144"
                elif "288" in nama_placemark: style_ref = "#style_jc_288"
                elif "EXT" in nama_placemark or "EXISTING" in nama_placemark: style_ref = "#style_jc_ext"
                else: style_ref = "#style_jc_ext"

            elif kategori_efektif == "SLACK HANGER":
                if "EXT" in nama_placemark or "EXISTING" in nama_placemark: style_ref = "#style_slack_ext"
                else: style_ref = "#style_slack_new"

            elif kategori_efektif == "OLT":
                style_ref = "#style_olt"

            elif kategori_efektif == "SLING WIRE":
                style_ref = "#shared_style_sling_wire"
                
            elif kategori_efektif in ["FAT", "HP COVER", "HP UNCOVER"]:
                style_ref = f"#shared_style_{kategori_efektif.replace(' ', '_')}"

            elif kategori_efektif == "FDT":
                desc_elem = placemark.find('kml:description', ns)
                if desc_elem is None: desc_elem = placemark.find('description')
                desc_text = desc_elem.text.strip().upper() if desc_elem is not None and desc_elem.text else ""
                
                fdt_style_ref = None
                if "96C" in desc_text: fdt_style_ref = "#shared_style_fdt_96c"
                elif "72C" in desc_text: fdt_style_ref = "#shared_style_fdt_72c"
                elif "48C" in desc_text: fdt_style_ref = "#shared_style_fdt_48c"
                elif "SHARING" in desc_text: fdt_style_ref = "#shared_style_fdt_sharing"
                    
                if fdt_style_ref is not None:
                    for tag_to_remove in ['kml:styleUrl', 'kml:Style', 'kml:StyleMap', 'styleUrl', 'Style', 'StyleMap']:
                        for elem_to_remove in list(placemark.findall(tag_to_remove, ns) + placemark.findall(tag_to_remove)):
                            placemark.remove(elem_to_remove)

                    style_url_elem = ET.SubElement(placemark, '{%s}styleUrl' % namespace_kml)
                    style_url_elem.text = fdt_style_ref

            if style_ref and kategori_efektif != "FDT":
                for tag_to_remove in ['kml:styleUrl', 'styleUrl']:
                    for elem_to_remove in list(placemark.findall(tag_to_remove, ns) + placemark.findall(tag_to_remove)):
                        placemark.remove(elem_to_remove)
                style_url_elem = ET.SubElement(placemark, '{%s}styleUrl' % namespace_kml)
                style_url_elem.text = style_ref

    # ==========================================
    # 5. LOGIKA PENYALINAN TITIK KE SLACK HANGER
    # ==========================================
    for folder_line in root.findall('.//kml:Folder', ns) + root.findall('.//Folder'):
        nama_line_elem = folder_line.find('kml:name', ns)
        if nama_line_elem is None: nama_line_elem = folder_line.find('name')
        
        if nama_line_elem is not None and nama_line_elem.text and nama_line_elem.text.strip().upper().startswith("LINE"):
            folder_fat = None
            folder_slack = None
            
            for sub_folder in folder_line.findall('./kml:Folder', ns) + folder_line.findall('./Folder'):
                sub_nama_elem = sub_folder.find('kml:name', ns)
                if sub_nama_elem is None: sub_nama_elem = sub_folder.find('name')
                
                if sub_nama_elem is not None and sub_nama_elem.text:
                    sub_nama = sub_nama_elem.text.strip().upper()
                    if sub_nama == "FAT": folder_fat = sub_folder
                    elif sub_nama == "SLACK HANGER": folder_slack = sub_folder
            
            if folder_fat is not None and folder_slack is not None:
                isi_slack = folder_slack.findall('./kml:Placemark', ns) + folder_slack.findall('./Placemark')
                if len(isi_slack) == 0:
                    for titik_fat in folder_fat.findall('./kml:Placemark', ns) + folder_fat.findall('./Placemark'):
                        placemark_copy = copy.deepcopy(titik_fat)
                        s_url = placemark_copy.find('kml:styleUrl', ns)
                        if s_url is None: s_url = placemark_copy.find('styleUrl')
                        if s_url is not None: s_url.text = "#style_slack_new"
                        else:
                            new_s_url = ET.SubElement(placemark_copy, '{%s}styleUrl' % namespace_kml)
                            new_s_url.text = "#style_slack_new"
                        folder_slack.append(placemark_copy)

    list_placemark_template = []
    for folder in root.findall('.//kml:Folder', ns) + root.findall('.//Folder'):
        kategori_efektif = get_kategori(folder)
        if kategori_efektif == "FDT":
            for titik_asli in folder.findall('./kml:Placemark', ns) + folder.findall('./Placemark'): 
                placemark_copy = copy.deepcopy(titik_asli) 

                tags_to_purge_copy = [
                    'kml:description', 'kml:Snippet', 'gx:balloonVisibility', 'description', 'Snippet', 'balloonVisibility',
                    'kml:TimeStamp', 'kml:TimeSpan', 'TimeStamp', 'TimeSpan', 'kml:ExtendedData', 'ExtendedData'
                ]
                for hapus_tag in tags_to_purge_copy:
                    tag_elem = placemark_copy.find(hapus_tag, ns)
                    if tag_elem is not None: placemark_copy.remove(tag_elem)
                        
                for tag_to_remove in ['kml:styleUrl', 'kml:Style', 'kml:StyleMap', 'styleUrl', 'Style', 'StyleMap']:
                    for elem_to_remove in list(placemark_copy.findall(tag_to_remove, ns) + placemark_copy.findall(tag_to_remove)):
                        placemark_copy.remove(elem_to_remove)

                nama_elem = placemark_copy.find('kml:name', ns)
                if nama_elem is None: nama_elem = placemark_copy.find('name')
                if nama_elem is None: nama_elem = ET.SubElement(placemark_copy, '{%s}name' % namespace_kml)
                nama_elem.text = "EXT.SLACK.FDT"

                style_url_elem = ET.SubElement(placemark_copy, '{%s}styleUrl' % namespace_kml)
                style_url_elem.text = "#shared_style_slack_hanger_copy"
                
                list_placemark_template.append(placemark_copy)

    if list_placemark_template:
        berhasil_paste = False
        for folder_induk in root.findall('.//kml:Folder', ns) + root.findall('.//Folder'):
            nama_induk = folder_induk.find('kml:name', ns)
            if nama_induk is None: nama_induk = folder_induk.find('name')
            if nama_induk is not None and nama_induk.text and nama_induk.text.strip().upper().startswith("LINE"):
                for folder_anak in folder_induk.findall('./kml:Folder', ns) + folder_induk.findall('./Folder'):
                    nama_anak = folder_anak.find('kml:name', ns)
                    if nama_anak is None: nama_anak = folder_anak.find('name')
                    if nama_anak is not None and nama_anak.text and nama_anak.text.strip().upper() == "SLACK HANGER":
                        for p_template in list_placemark_template:
                            folder_anak.append(copy.deepcopy(p_template))
                        berhasil_paste = True
                        break
            if berhasil_paste: break

    # ==========================================
    # 6. PEMBERSIHAN FOLDER KOSONG (KHUSUS PRE ABD / ABD)
    # ==========================================
    if format_tahapan == "PRE ABD / ABD":
        def bersihkan_folder_kosong(elemen):
            # Cek anak Folder secara rekursif
            anak_folder = [e for e in elemen if e.tag.split('}')[-1] == 'Folder']
            for f in anak_folder:
                bersihkan_folder_kosong(f)
                
                # Cek apakah folder tersebut punya Placemark, GroundOverlay, NetworkLink, atau Subfolder
                punya_placemark = len(f.findall('.//{%s}Placemark' % namespace_kml) + f.findall('.//Placemark')) > 0
                punya_subfolder = any(sub.tag.split('}')[-1] == 'Folder' for sub in f)
                punya_konten_lain = any(sub.tag.split('}')[-1] in ['GroundOverlay', 'NetworkLink', 'ScreenOverlay'] for sub in f)
                
                if not (punya_placemark or punya_subfolder or punya_konten_lain):
                    elemen.remove(f)

        bersihkan_folder_kosong(root)

    tree.write(file_kml, encoding='utf-8', xml_declaration=True)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as new_kmz:
        for root_dir, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root_dir, file)
                arcname = os.path.relpath(file_path, extract_dir)
                new_kmz.write(file_path, arcname)

# ==========================================
# ANTARMUKA WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Universal KMZ Formatter", page_icon="🌍")

st.title("🌍 Universal KMZ Auto-Formatter & Multi-Renamer")
st.write("Standarisasi format Cluster/Subfeeder/Feeder, penamaan FO Cable, Multi Rename, dan opsi filter folder kosong.")

col_pilihan1, col_pilihan2 = st.columns(2)
with col_pilihan1:
    tipe_kmz = st.selectbox("📌 Tipe KMZ:", ["Cluster", "Subfeeder", "Feeder"])
with col_pilihan2:
    format_tahapan = st.selectbox("📂 Format Tahapan KMZ:", ["APD", "PRE ABD / ABD"])

if format_tahapan == "PRE ABD / ABD":
    st.caption("ℹ️ Mode PRE ABD / ABD aktif: Semua folder standar yang tidak memiliki objek/placemark akan otomatis dihapus.")

st.markdown("---")
st.subheader("✏️ Fitur Multi Rename Massal (Find & Replace)")
st.write("Masukkan teks lama yang ingin dicari dan teks penggantinya pada 4 slot di bawah ini secara bersamaan:")

col1, col2 = st.columns(2)
with col1:
    cari1 = st.text_input("Cari Teks 1", placeholder="Contoh: ABCD")
    cari2 = st.text_input("Cari Teks 2", placeholder="")
    cari3 = st.text_input("Cari Teks 3", placeholder="")
    cari4 = st.text_input("Cari Teks 4", placeholder="")

with col2:
    ganti1 = st.text_input("Ganti Menjadi 1", placeholder="Contoh: ABCE")
    ganti2 = st.text_input("Ganti Menjadi 2", placeholder="")
    ganti3 = st.text_input("Ganti Menjadi 3", placeholder="")
    ganti4 = st.text_input("Ganti Menjadi 4", placeholder="")

list_rename = [
    (cari1, ganti1),
    (cari2, ganti2),
    (cari3, ganti3),
    (cari4, ganti4)
]

st.markdown("---")
uploaded_file = st.file_uploader(f"Unggah file KMZ ({tipe_kmz} - {format_tahapan})", type=["kmz"])

if uploaded_file is not None:
    st.info("File berhasil diunggah!")
    
    if st.button("🚀 Proses, Standarisasi & Filter KMZ"):
        with st.spinner(f'Memproses {tipe_kmz} dengan format {format_tahapan}...'):
            try:
                temp_dir = tempfile.mkdtemp()
                input_path = os.path.join(temp_dir, "input.kmz")
                output_path = os.path.join(temp_dir, "output.kmz")
                extract_dir = os.path.join(temp_dir, "extracted")
                
                with open(input_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                proses_kmz(input_path, output_path, extract_dir, tipe_kmz, format_tahapan, list_rename)
                
                with open(output_path, "rb") as f:
                    hasil_bytes = f.read()
                
                pesan_sukses = f"Berhasil! KMZ diproses untuk {tipe_kmz} ({format_tahapan})."
                if format_tahapan == "PRE ABD / ABD":
                    pesan_sukses += " Folder-folder kosong telah dibersihkan."
                st.success(pesan_sukses)
                
                nama_file_hasil = f"{format_tahapan.replace(' ', '_').replace('/', '_')}_{tipe_kmz}_{uploaded_file.name}"
                st.download_button(
                    label="⬇️ Download File KMZ Hasil",
                    data=hasil_bytes,
                    file_name=nama_file_hasil,
                    mime="application/vnd.google-earth.kmz"
                )
                
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
            finally:
                if 'temp_dir' in locals():
                    shutil.rmtree(temp_dir)
