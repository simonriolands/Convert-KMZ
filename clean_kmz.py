import io
import re
import zipfile
import xml.etree.ElementTree as ET

# Regex untuk mendeteksi karakter tak terlihat (Zero-Width Space U+200B, BOM, Control Chars, dll.)
GHOST_REGEX = re.compile(
    r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F\u00AD\u034F\u061C\u180E\u200B-\u200F\u202A-\u202E\u2060-\u206F\u3164\uFEFF\uFFA0]"
)

# Regex untuk spasi non-standar (NBSP U+00A0, dll.)
WEIRD_SPACE_REGEX = re.compile(r"[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]")


def get_local_tag(tag):
  """Menghilangkan namespace XML agar mudah dicocokkan"""
  return tag.split("}")[-1]


def get_direct_name_node(element):
  """Mencari tag <name> anak langsung dari sebuah elemen"""
  for child in element:
    if get_local_tag(child.tag) == "name":
      return child
  return None


def get_element_folder_path(element, parent_map):
  """Membangun jalur hierarki folder (contoh: LINE B - FDT 01 / HP COVER / B02)"""
  path_parts = []
  curr = parent_map.get(element)
  while curr is not None:
    tag = get_local_tag(curr.tag)
    if tag in ("Folder", "Placemark"):
      name_node = get_direct_name_node(curr)
      if name_node is not None and name_node.text:
        clean_name = (
            GHOST_REGEX.sub("", name_node.text)
            .replace("\u00A0", " ")
            .strip()
        )
        if clean_name:
          path_parts.insert(0, clean_name)
    curr = parent_map.get(curr)
  return " / ".join(path_parts) if path_parts else "(Root Document)"


def is_inside_fdt_folder(element, parent_map):
  """Mengecek apakah elemen berada di dalam Folder bernama persis 'FDT'"""
  curr = parent_map.get(element)
  while curr is not None:
    tag = get_local_tag(curr.tag)
    if tag == "Folder":
      name_node = get_direct_name_node(curr)
      if name_node is not None and name_node.text:
        folder_name = (
            GHOST_REGEX.sub("", name_node.text)
            .replace("\u00A0", " ")
            .strip()
            .toUpperCase()
        )
        if folder_name == "FDT":
          return True
    curr = parent_map.get(curr)
  return False


def process_kmz_bytes(file_bytes, filename):
  is_kmz = filename.lower().endswith(".kmz")
  kml_content = ""
  kml_filename = "doc.kml"

  # 1. Ekstrak KML dari KMZ atau baca teks KML langsung
  if is_kmz:
    with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
      kml_files = [
          n
          for n in zf.namelist()
          if n.lower().endswith(".kml") and not zf.getinfo(n).is_dir()
      ]
      if not kml_files:
        raise ValueError("File .kml tidak ditemukan di dalam arsip KMZ.")
      kml_filename = kml_files[0]
      with zf.open(kml_filename) as f:
        kml_content = f.read().decode("utf-8")
  else:
    kml_content = file_bytes.decode("utf-8")

  # 2. Parsing XML KML
  ET.register_namespace("", "http://www.opengis.net/kml/2.2")
  kml_content = kml_content.lstrip("\ufeff")
  root = ET.fromstring(kml_content)
  parent_map = {c: p for p in root.iter() for c in p}

  changes_log = []

  # 3. Iterasi seluruh elemen mencari tag <name> dan <SimpleData>
  for elem in root.iter():
    tag_name = get_local_tag(elem.tag)
    if tag_name in ("name", "SimpleData"):
      if elem.text is None:
        continue
      original_text = elem.text
      new_text = original_text
      issues = []

      # A. Hapus spasi siluman (U+200B, dll.)
      ghost_matches = GHOST_REGEX.findall(new_text)
      if ghost_matches:
        ghost_codes = [
            f"U+{ord(c):04X}" for c in sorted(list(set(ghost_matches)))
        ]
        issues.append(f"Spasi Siluman ({', '.join(ghost_codes)})")
        new_text = GHOST_REGEX.sub("", new_text)

      # B. Normalisasi NBSP
      if WEIRD_SPACE_REGEX.search(new_text):
        issues.append("Spasi Non-Standar")
        new_text = WEIRD_SPACE_REGEX.sub(" ", new_text)

      # C. Logika Folder FDT vs Auto-Trim
      in_fdt = is_inside_fdt_folder(elem, parent_map)
      if in_fdt and re.search(r"\s+", new_text):
        issues.append("Spasi Folder FDT Dihapus")
        new_text = re.sub(r"\s+", "", new_text)
      else:
        if new_text != new_text.strip():
          issues.append("Spasi Ujung (Trim)")
          new_text = new_text.strip()

      # D. Catat perubahan
      if original_text != new_text:
        elem.text = new_text
        parent_el = parent_map.get(elem)
        item_type = (
            f"SimpleData ({elem.attrib.get('name', 'attr')})"
            if tag_name == "SimpleData"
            else (
                get_local_tag(parent_el.tag)
                if parent_el is not None
                else "Item"
            )
        )
        folder_path = get_element_folder_path(parent_el or elem, parent_map)

        changes_log.append({
            "type": item_type,
            "path": folder_path,
            "issues": ", ".join(issues),
            "old": original_text,
            "new": new_text,
        })

  # 4. Serialize kembali ke format XML
  updated_kml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode(
      "utf-8"
  )

  # 5. Kembalikan file hasil pembersihan
  if is_kmz:
    output_buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zin:
      with zipfile.ZipFile(
          output_buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=6
      ) as zout:
        for item in zin.infolist():
          buffer = zin.read(item.filename)
          if item.filename == kml_filename:
            buffer = updated_kml_str.encode("utf-8")
          zout.writestr(item, buffer)
    return output_buffer.getvalue(), changes_log
  else:
    return updated_kml_str.encode("utf-8"), changes_log