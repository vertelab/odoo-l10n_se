import csv
import xml.etree.ElementTree as ET
import os


# def process_xml_record(xml_record):
#     _id = xml_record.find("./field[@name='code']").text
#     code = xml_record.find("./field[@name='code']").text
#     name = xml_record.find("./field[@name='name']").text.strip()
#     account_type = xml_record.find("./field[@name='account_type']").text
#     reconcile = xml_record.find("./field[@name='reconcile']")
#
#     return {
#         "id": f"a{_id}",
#         "code": code,  # Assuming an empty value or a default value
#         "name": name,
#         "account_type": account_type,  # Assuming an empty value or a default value
#         "reconcile": reconcile is not None,
#         "name@sv_SE": name
#     }
#
#
# current_file_path = __file__
# current_dir = os.path.dirname(os.path.abspath(current_file_path))
#
# xml_file_path = f"{current_dir}/template/account_chart_template_k3.xml"
# csv_file_path = f"{current_dir}/template/account.account-extended_se_K3.csv"
#
# # Check if CSV file exists and has content
# file_exists = os.path.isfile(csv_file_path) and os.path.getsize(csv_file_path) > 0
#
# # Read XML file and process each record
# tree = ET.parse(xml_file_path)
# root = tree.getroot()
#
# data_element = root.find('data')
#
# with open(csv_file_path, 'a', newline='', encoding='utf-8') as file:
#     writer = csv.DictWriter(file,
#                             fieldnames=["id", "code", "name", "account_type", "reconcile", "name@sv_SE"])
#     # Write the header only if the file didn't exist or was empty
#     if not file_exists:
#         writer.writeheader()
#
#     for record in data_element.findall('record'):
#         if record.attrib['model'] == 'account.account.template':
#             csv_data = process_xml_record(record)
#             writer.writerow(csv_data)
#
# print("CSV file updated with the new data.")


current_file_path = __file__
current_dir = os.path.dirname(os.path.abspath(current_file_path))

input_file = f"{current_dir}/template/sample-account.tax-se.csv"
output_file = f"{current_dir}/template/account.tax-se.csv"

# Check if CSV file exists and has content
file_exists = os.path.isfile(output_file) and os.path.getsize(output_file) > 0


with open(input_file, mode='r', newline='', encoding='utf-8') as infile, \
     open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile, quoting=csv.QUOTE_ALL)

    for row in reader:
        # Write each row to the new file, with all fields quoted
        writer.writerow(row)

print("File has been written with all fields quoted.")


