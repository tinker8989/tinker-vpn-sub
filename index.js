import express from "express";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const app = express();
const PORT = process.env.PORT || 3000;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const STANDARD_FILE = path.join(__dirname, "standard.txt");
const PREMIUM_FILE = path.join(__dirname, "premium.txt");
const FAMILY_FILE = path.join(__dirname, "family.txt");

function setHeaders(res, title) {
  const expire = Math.floor(new Date("2390-09-02T00:00:00Z").getTime() / 1000);

  res.setHeader("Content-Type", "text/plain; charset=utf-8");
  res.setHeader("Profile-Title", title);
  res.setHeader("Profile-Update-Interval", "1");
  res.setHeader("Subscription-Userinfo", `upload=0; download=0; total=0; expire=${expire}`);
  res.setHeader("Profile-Web-Page-URL", "https://t.me/tinker_vpn");
}

function sendFile(res, filePath, title) {
  if (!fs.existsSync(filePath)) {
    return res.status(404).send("Not found");
  }

  setHeaders(res, title);

  const data = fs.readFileSync(filePath, "utf-8");
  res.send(data);
}

// проверка
app.get("/", (req, res) => {
  res.send("Tinker VPN server working 🚀");
});

// подписки
app.get("/standard", (req, res) => {
  sendFile(res, STANDARD_FILE, "Tinker VPN Standart");
});

app.get("/premium", (req, res) => {
  sendFile(res, PREMIUM_FILE, "Tinker VPN Premium");
});

app.get("/family", (req, res) => {
  sendFile(res, FAMILY_FILE, "Tinker VPN Family");
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
