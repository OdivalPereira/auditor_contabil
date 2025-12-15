import os

path = r"c:\Users\contabil\Documents\Projetos Antigravity\extração_pdfs"
file_name = "MCM set25.pdf"
full_path = os.path.join(path, file_name)

print(f"Checking {full_path}")
if os.path.exists(full_path):
    print("File EXISTS")
else:
    print("File NOT FOUND")
    print("Listing directory:")
    for f in os.listdir(path):
        print(f)
