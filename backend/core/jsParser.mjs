// jsParser.js
import fs from "fs";
import path from "path";
import { transform } from "lebab";

function upgradeJSFile(srcPath, destPath) {
  const originalCode = fs.readFileSync(srcPath, "utf-8");

  const { code, warnings } = transform(originalCode, [
    "arrow",
    "let",
    "template",
    "default-param",
    "includes",
    "for-of",
    "destruct-param",
    "class"
  ]);

  if (warnings.length) {
    console.warn("Lebab Warnings:", warnings);
  }

  fs.mkdirSync(path.dirname(destPath), { recursive: true });
  fs.writeFileSync(destPath, code, "utf-8");

  console.log(`Upgraded JS: ${destPath}`);
}

// CLI usage
const [,, src, dest] = process.argv;
if (!src || !dest) {
  console.error("Usage: node jsParser.js <source.js> <destination.js>");
  process.exit(1);
}
upgradeJSFile(src, dest);
