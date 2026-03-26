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

const TG_URL = "https://t.me/tinkervpn";
const UPDATE_INTERVAL_HOURS = 1;
const UPDATE_INTERVAL_SECONDS = UPDATE_INTERVAL_HOURS * 3600;

function cleanText(text) {
  return String(text || "").replace(/^\uFEFF/, "").trim();
}

function setHeaders(res, title) {
  res.setHeader("Content-Type", "text/plain; charset=utf-8");

  // Название подписки
  res.setHeader("Profile-Title", title);
  res.setHeader("X-Profile-Title", title);

  // Автообновление раз в час
  res.setHeader("Profile-Update-Interval", String(UPDATE_INTERVAL_HOURS));
  res.setHeader("X-Profile-Update-Interval", String(UPDATE_INTERVAL_HOURS));

  // Ссылка/кнопка с инфой и телеграмом
  res.setHeader("Profile-Web-Page-URL", TG_URL);
  res.setHeader("X-Profile-Web-Page-URL", TG_URL);
  res.setHeader("Support-URL", TG_URL);
  res.setHeader("X-Support-URL", TG_URL);

  // Без срока окончания подписки
  res.setHeader(
    "Subscription-Userinfo",
    "upload=0; download=0; total=0"
  );
  res.setHeader(
    "X-Subscription-Userinfo",
    "upload=0; download=0; total=0"
  );

  // Для части клиентов полезно
  res.setHeader("Cache-Control", `public, max-age=${UPDATE_INTERVAL_SECONDS}`);
}

function sendSubscription(res, filePath, title) {
  try {
    if (!fs.existsSync(filePath)) {
      return res.status(404).send("Subscription file not found");
    }

    let data = fs.readFileSync(filePath, "utf-8");
    data = cleanText(data);

    if (!data) {
      return res.status(500).send("Subscription file is empty");
    }

    setHeaders(res, title);
    return res.status(200).send(data);
  } catch (e) {
    console.error("Send subscription error:", e);
    return res.status(500).send("Internal server error");
  }
}

// Главная
app.get("/", (req, res) => {
  res.status(200).send("Tinker VPN subscription server is working");
});

// Нормализация двойных слешей
app.use((req, res, next) => {
  if (req.path.includes("//")) {
    const normalized = req.path.replace(/\/{2,}/g, "/");
    return res.redirect(301, normalized);
  }
  next();
});

// Подписки
app.get("/standard", (req, res) => {
  sendSubscription(res, STANDARD_FILE, "Tinker VPN Standard");
});

// Алиас если где-то осталось старое написание
app.get("/standart", (req, res) => {
  sendSubscription(res, STANDARD_FILE, "Tinker VPN Standard");
});

app.get("/premium", (req, res) => {
  sendSubscription(res, PREMIUM_FILE, "Tinker VPN Premium");
});

app.get("/family", (req, res) => {
  sendSubscription(res, FAMILY_FILE, "Tinker VPN Family");
});

// 404
app.use((req, res) => {
  res.status(404).send("Not found");
});

app.listen(PORT, () => {
  console.log(`Tinker VPN server running on port ${PORT}`);
});
