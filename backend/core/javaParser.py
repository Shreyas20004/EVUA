import os
import sys
import argparse
import xml.etree.ElementTree as ET
import re

def detect_build_system(project_path):
    if os.path.exists(os.path.join(project_path, "pom.xml")):
        return "maven"
    if os.path.exists(os.path.join(project_path, "build.gradle")):
        return "gradle"
    return None

# ---------- Maven POM Upgrader ----------
def upgrade_maven_pom(pom_path, target_version):
    tree = ET.parse(pom_path)
    root = tree.getroot()
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}

    changed = False
    for prop in root.findall("m:properties/*", ns):
        if prop.tag.endswith("source") or prop.tag.endswith("target"):
            old = prop.text
            prop.text = target_version
            print(f"  - Updated {prop.tag} {old} → {target_version}")
            changed = True

    if not changed:  # if <properties> missing, add it
        props = root.find("m:properties", ns)
        if props is None:
            props = ET.SubElement(root, "properties")
        ET.SubElement(props, "maven.compiler.source").text = target_version
        ET.SubElement(props, "maven.compiler.target").text = target_version
        print("  - Added maven.compiler.source/target")

    tree.write(pom_path, encoding="utf-8", xml_declaration=True)
    print(f"✅ {pom_path} updated to Java {target_version}")

# ---------- Gradle build.gradle Upgrader ----------
def upgrade_gradle_build(build_path, target_version):
    with open(build_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace JavaVersion.VERSION_1_8 → VERSION_21
    content = re.sub(r"JavaVersion\.VERSION_\d+_\d+", f"JavaVersion.VERSION_{target_version}", content)
    # Replace source/targetCompatibility = '1.8'
    content = re.sub(r"(sourceCompatibility\s*=\s*['\"])\d+(\.?\d*)(['\"])", fr"\g<1>{target_version}\3", content)
    content = re.sub(r"(targetCompatibility\s*=\s*['\"])\d+(\.?\d*)(['\"])", fr"\g<1>{target_version}\3", content)

    with open(build_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ {build_path} updated to Java {target_version}")

# ---------- Java Source Scanner ----------
def upgrade_java_sources(project_path, target_version):
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()

                original = code

                # Example transformations:
                code = code.replace("import java.util.Date;", "import java.time.LocalDate;")
                code = code.replace("new Date()", "LocalDate.now()")
                code = re.sub(r"System\.getProperty\(\"line\.separator\"\)", "System.lineSeparator()", code)

                if code != original:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(code)
                    print(f"  ⚡ Upgraded Java file: {file_path}")

# ---------- Main Runner ----------
def main():
    parser = argparse.ArgumentParser(description="Hybrid Java Project Upgrader")
    parser.add_argument("--path", required=True, help="Project root path")
    parser.add_argument("--target", required=True, help="Target Java version (e.g., 17, 21)")
    args = parser.parse_args()

    project_path = os.path.abspath(args.path)
    target_version = args.target

    print(f"🔍 Scanning project at {project_path}")
    build_system = detect_build_system(project_path)

    if build_system == "maven":
        print("📦 Maven project detected")
        pom_path = os.path.join(project_path, "pom.xml")
        upgrade_maven_pom(pom_path, target_version)
    elif build_system == "gradle":
        print("📦 Gradle project detected")
        build_path = os.path.join(project_path, "build.gradle")
        upgrade_gradle_build(build_path, target_version)
    else:
        print("❌ No supported build system detected (Maven/Gradle)")
        sys.exit(1)

    print("🔧 Scanning and upgrading Java sources...")
    upgrade_java_sources(project_path, target_version)

    print(f"🎉 Upgrade complete! Project is now set to Java {target_version}")

if __name__ == "__main__":
    main()
