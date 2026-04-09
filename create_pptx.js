const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const {
  FaHospital, FaUserPlus, FaLock, FaFileDownload, FaKey, FaClipboardList,
  FaShieldAlt, FaServer, FaLink, FaCheckCircle, FaEthereum
} = require("react-icons/fa");

// ---- Icon helper ----
function renderIconSvg(IconComponent, color, size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}
async function iconToBase64(IconComponent, color, size = 256) {
  const svg = renderIconSvg(IconComponent, color, size);
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ---- Palette (matching the website: teal + sienna + cream) ----
const C = {
  tealDeep: "0D4F4F",
  teal: "147A7A",
  tealLight: "E4F0EF",
  sienna: "C45D3E",
  siennaLight: "FCEEE9",
  cream: "F6F1EA",
  paper: "FFFFFF",
  ink: "1A1A1A",
  inkSec: "4A4A4A",
  inkMuted: "8C8C8C",
  sage: "5F8A72",
  sageLight: "EAF2EC",
};

// ---- Factory helpers (avoid object reuse pitfall) ----
const shadow = () => ({ type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.10 });
const cardShadow = () => ({ type: "outer", blur: 12, offset: 4, angle: 135, color: "000000", opacity: 0.08 });

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "BlockMedChain";
  pres.title = "BlockMedChain - Secure Health Records on Blockchain";

  // Pre-render icons
  const icons = {
    hospital:  await iconToBase64(FaHospital, "#FFFFFF"),
    userPlus:  await iconToBase64(FaUserPlus, "#FFFFFF"),
    lock:      await iconToBase64(FaLock, "#FFFFFF"),
    download:  await iconToBase64(FaFileDownload, "#FFFFFF"),
    key:       await iconToBase64(FaKey, "#FFFFFF"),
    clipboard: await iconToBase64(FaClipboardList, "#FFFFFF"),
    shield:    await iconToBase64(FaShieldAlt, "#FFFFFF"),
    server:    await iconToBase64(FaServer, "#FFFFFF"),
    link:      await iconToBase64(FaLink, "#FFFFFF"),
    check:     await iconToBase64(FaCheckCircle, "#FFFFFF"),
    eth:       await iconToBase64(FaEthereum, "#FFFFFF"),
    // Dark versions for light backgrounds
    hospitalD: await iconToBase64(FaHospital, "#0D4F4F"),
    lockD:     await iconToBase64(FaLock, "#C45D3E"),
    shieldD:   await iconToBase64(FaShieldAlt, "#0D4F4F"),
    keyD:      await iconToBase64(FaKey, "#0D4F4F"),
    checkD:    await iconToBase64(FaCheckCircle, "#5F8A72"),
    clipD:     await iconToBase64(FaClipboardList, "#0D4F4F"),
  };

  // ================================================================
  // SLIDE 1: Title
  // ================================================================
  let s1 = pres.addSlide();
  s1.background = { color: C.tealDeep };
  // Decorative circles
  s1.addShape(pres.shapes.OVAL, { x: -1.5, y: -1.5, w: 4, h: 4, fill: { color: C.teal, transparency: 70 } });
  s1.addShape(pres.shapes.OVAL, { x: 7.5, y: 3, w: 5, h: 5, fill: { color: C.sienna, transparency: 80 } });
  // Icon
  s1.addImage({ data: icons.hospital, x: 4.5, y: 0.6, w: 1, h: 1 });
  // Title
  s1.addText("BlockMedChain", {
    x: 0.5, y: 1.8, w: 9, h: 1.2,
    fontSize: 48, fontFace: "Georgia", bold: true,
    color: C.paper, align: "center", margin: 0
  });
  // Subtitle
  s1.addText("Secure Health Records on Blockchain", {
    x: 1, y: 3.0, w: 8, h: 0.6,
    fontSize: 20, fontFace: "Calibri",
    color: C.siennaLight, align: "center"
  });
  // Tagline
  s1.addText("AHE-DHA Encryption  |  Ethereum Smart Contracts  |  Patient-Controlled Access", {
    x: 1, y: 3.8, w: 8, h: 0.5,
    fontSize: 12, fontFace: "Calibri",
    color: C.tealLight, align: "center"
  });

  // ================================================================
  // SLIDE 2: Problem Statement
  // ================================================================
  let s2 = pres.addSlide();
  s2.background = { color: C.cream };
  s2.addText("The Problem", {
    x: 0.8, y: 0.4, w: 8, h: 0.8,
    fontSize: 36, fontFace: "Georgia", bold: true, color: C.tealDeep, margin: 0
  });
  s2.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 1.15, w: 1.2, h: 0.05, fill: { color: C.sienna } });

  const problems = [
    { title: "Data Breaches", desc: "Health records are stolen every day from centralised databases" },
    { title: "No Patient Control", desc: "Patients cannot see or control who accesses their medical data" },
    { title: "No Audit Trail", desc: "There is no tamper-proof log of who viewed or changed a record" },
  ];
  problems.forEach((p, i) => {
    const y = 1.7 + i * 1.2;
    s2.addShape(pres.shapes.RECTANGLE, { x: 0.8, y, w: 8.4, h: 1.0, fill: { color: C.paper }, shadow: cardShadow() });
    s2.addShape(pres.shapes.RECTANGLE, { x: 0.8, y, w: 0.08, h: 1.0, fill: { color: C.sienna } });
    s2.addText(p.title, { x: 1.2, y: y + 0.1, w: 7.5, h: 0.35, fontSize: 16, fontFace: "Georgia", bold: true, color: C.ink, margin: 0 });
    s2.addText(p.desc, { x: 1.2, y: y + 0.5, w: 7.5, h: 0.35, fontSize: 13, fontFace: "Calibri", color: C.inkSec, margin: 0 });
  });

  // ================================================================
  // SLIDE 3: Our Solution
  // ================================================================
  let s3 = pres.addSlide();
  s3.background = { color: C.cream };
  s3.addText("Our Solution", {
    x: 0.8, y: 0.4, w: 8, h: 0.8,
    fontSize: 36, fontFace: "Georgia", bold: true, color: C.tealDeep, margin: 0
  });
  s3.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 1.15, w: 1.2, h: 0.05, fill: { color: C.sienna } });

  s3.addText("BlockMedChain combines blockchain and advanced encryption to give patients full control over their health records.", {
    x: 0.8, y: 1.5, w: 8.4, h: 0.7,
    fontSize: 15, fontFace: "Calibri", color: C.inkSec
  });

  const pillars = [
    { icon: icons.lockD, title: "AHE-DHA Encryption", desc: "Hybrid AES + RSA encryption with sensitivity scoring" },
    { icon: icons.shieldD, title: "Smart Contracts", desc: "On-chain access control, storage hashes, and audit events" },
    { icon: icons.keyD, title: "Patient Ownership", desc: "Only patients hold the keys and decide who sees their data" },
  ];
  pillars.forEach((p, i) => {
    const x = 0.8 + i * 3.0;
    s3.addShape(pres.shapes.RECTANGLE, { x, y: 2.5, w: 2.7, h: 2.6, fill: { color: C.paper }, shadow: cardShadow() });
    // Icon circle
    s3.addShape(pres.shapes.OVAL, { x: x + 0.85, y: 2.75, w: 1.0, h: 1.0, fill: { color: C.tealLight } });
    s3.addImage({ data: p.icon, x: x + 1.05, y: 2.95, w: 0.6, h: 0.6 });
    s3.addText(p.title, { x: x + 0.15, y: 3.9, w: 2.4, h: 0.4, fontSize: 14, fontFace: "Georgia", bold: true, color: C.tealDeep, align: "center", margin: 0 });
    s3.addText(p.desc, { x: x + 0.15, y: 4.3, w: 2.4, h: 0.6, fontSize: 11, fontFace: "Calibri", color: C.inkMuted, align: "center" });
  });

  // ================================================================
  // SLIDE 4: Patient Registration
  // ================================================================
  let s4 = pres.addSlide();
  s4.background = { color: C.cream };
  s4.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 4.2, h: 5.625, fill: { color: C.tealDeep } });
  // Left side content
  s4.addImage({ data: icons.userPlus, x: 1.5, y: 1.2, w: 1.2, h: 1.2 });
  s4.addText("Patient\nRegistration", {
    x: 0.4, y: 2.6, w: 3.4, h: 1.2,
    fontSize: 28, fontFace: "Georgia", bold: true, color: C.paper, align: "center", margin: 0
  });
  s4.addText("STEP 1", {
    x: 1.2, y: 0.5, w: 1.8, h: 0.4,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.sienna, align: "center",
    charSpacing: 4
  });
  // Right side
  const regSteps = [
    "Patient chooses a unique ID (e.g. patient_001)",
    "System links the ID to a blockchain wallet address",
    "RSA key pair is generated for encryption",
    "Identity is recorded on-chain via PatientRegistry contract",
    "Public key is shared; private key stays with the patient",
  ];
  regSteps.forEach((step, i) => {
    const y = 0.8 + i * 0.85;
    s4.addShape(pres.shapes.OVAL, { x: 4.8, y: y + 0.05, w: 0.35, h: 0.35, fill: { color: C.teal } });
    s4.addText(String(i + 1), { x: 4.8, y: y + 0.05, w: 0.35, h: 0.35, fontSize: 12, fontFace: "Calibri", bold: true, color: C.paper, align: "center", valign: "middle" });
    s4.addText(step, { x: 5.35, y: y, w: 4.2, h: 0.5, fontSize: 13, fontFace: "Calibri", color: C.inkSec, valign: "middle" });
  });

  // ================================================================
  // SLIDE 5: EHR Upload
  // ================================================================
  let s5 = pres.addSlide();
  s5.background = { color: C.cream };
  s5.addText("Encrypt & Upload Records", {
    x: 0.8, y: 0.4, w: 8, h: 0.8,
    fontSize: 36, fontFace: "Georgia", bold: true, color: C.tealDeep, margin: 0
  });
  s5.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 1.15, w: 1.8, h: 0.05, fill: { color: C.sienna } });

  // Flow diagram
  const flow = [
    { label: "Health\nRecord", color: C.sage },
    { label: "AHE-DHA\nEncrypt", color: C.sienna },
    { label: "Store\nOff-chain", color: C.teal },
    { label: "Hash on\nBlockchain", color: C.tealDeep },
  ];
  flow.forEach((f, i) => {
    const x = 0.6 + i * 2.4;
    s5.addShape(pres.shapes.RECTANGLE, { x, y: 1.7, w: 2.0, h: 1.3, fill: { color: f.color }, shadow: shadow() });
    s5.addText(f.label, { x, y: 1.7, w: 2.0, h: 1.3, fontSize: 16, fontFace: "Georgia", bold: true, color: C.paper, align: "center", valign: "middle" });
    if (i < flow.length - 1) {
      s5.addText("\u2192", { x: x + 2.0, y: 1.95, w: 0.4, h: 0.8, fontSize: 28, color: C.inkMuted, align: "center", valign: "middle" });
    }
  });

  // Details
  const uploadDetails = [
    "Each record gets a unique AES-256 session key (one-time use)",
    "The session key is wrapped with the patient's RSA public key",
    "Encrypted file is saved to local storage (off-chain)",
    "SHA-256 hash of the file is written to the EHRStorage smart contract",
    "A sensitivity score is calculated based on the data fields",
  ];
  uploadDetails.forEach((d, i) => {
    s5.addText(d, {
      x: 0.8, y: 3.35 + i * 0.42, w: 8.4, h: 0.38,
      fontSize: 12, fontFace: "Calibri", color: C.inkSec,
      bullet: true
    });
  });

  // ================================================================
  // SLIDE 6: Record Retrieval
  // ================================================================
  let s6 = pres.addSlide();
  s6.background = { color: C.cream };
  s6.addShape(pres.shapes.RECTANGLE, { x: 5.8, y: 0, w: 4.2, h: 5.625, fill: { color: C.tealDeep } });
  // Right side
  s6.addImage({ data: icons.download, x: 7.4, y: 1.2, w: 1.2, h: 1.2 });
  s6.addText("Retrieve &\nDecrypt", {
    x: 6.2, y: 2.6, w: 3.4, h: 1.2,
    fontSize: 28, fontFace: "Georgia", bold: true, color: C.paper, align: "center", margin: 0
  });
  s6.addText("STEP 3", {
    x: 7.0, y: 0.5, w: 1.8, h: 0.4,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.sienna, align: "center",
    charSpacing: 4
  });
  // Left side
  const retrieveSteps = [
    "Provider requests a record by Patient ID and Record ID",
    "System fetches the hash stored on the blockchain",
    "Off-chain file is loaded and its hash is compared",
    "If hashes match, integrity is verified",
    "Record is decrypted using the patient's private key",
  ];
  retrieveSteps.forEach((step, i) => {
    const y = 0.8 + i * 0.85;
    s6.addShape(pres.shapes.OVAL, { x: 0.6, y: y + 0.05, w: 0.35, h: 0.35, fill: { color: C.teal } });
    s6.addText(String(i + 1), { x: 0.6, y: y + 0.05, w: 0.35, h: 0.35, fontSize: 12, fontFace: "Calibri", bold: true, color: C.paper, align: "center", valign: "middle" });
    s6.addText(step, { x: 1.15, y: y, w: 4.3, h: 0.5, fontSize: 13, fontFace: "Calibri", color: C.inkSec, valign: "middle" });
  });

  // ================================================================
  // SLIDE 7: Access Control
  // ================================================================
  let s7 = pres.addSlide();
  s7.background = { color: C.cream };
  s7.addText("Access Control", {
    x: 0.8, y: 0.4, w: 8, h: 0.8,
    fontSize: 36, fontFace: "Georgia", bold: true, color: C.tealDeep, margin: 0
  });
  s7.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 1.15, w: 1.2, h: 0.05, fill: { color: C.sienna } });

  s7.addText("Patients have full control. Only the wallet owner can grant or revoke access.", {
    x: 0.8, y: 1.5, w: 8.4, h: 0.5,
    fontSize: 15, fontFace: "Calibri", color: C.inkSec
  });

  // Two cards: Grant and Revoke
  // Grant
  s7.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 2.4, w: 4.0, h: 2.6, fill: { color: C.paper }, shadow: cardShadow() });
  s7.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 2.4, w: 4.0, h: 0.08, fill: { color: C.sage } });
  s7.addText("Grant Access", { x: 1.1, y: 2.7, w: 3.4, h: 0.45, fontSize: 18, fontFace: "Georgia", bold: true, color: C.sage, margin: 0 });
  s7.addText([
    { text: "Patient selects a provider wallet address", options: { bullet: true, breakLine: true } },
    { text: "Smart contract records the permission on-chain", options: { bullet: true, breakLine: true } },
    { text: "Provider can now retrieve and decrypt records", options: { bullet: true, breakLine: true } },
    { text: "AccessGranted event is emitted for audit", options: { bullet: true } },
  ], { x: 1.1, y: 3.3, w: 3.4, h: 1.5, fontSize: 12, fontFace: "Calibri", color: C.inkSec });

  // Revoke
  s7.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 2.4, w: 4.0, h: 2.6, fill: { color: C.paper }, shadow: cardShadow() });
  s7.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 2.4, w: 4.0, h: 0.08, fill: { color: C.sienna } });
  s7.addText("Revoke Access", { x: 5.5, y: 2.7, w: 3.4, h: 0.45, fontSize: 18, fontFace: "Georgia", bold: true, color: C.sienna, margin: 0 });
  s7.addText([
    { text: "Patient can revoke any provider at any time", options: { bullet: true, breakLine: true } },
    { text: "Permission is removed instantly on-chain", options: { bullet: true, breakLine: true } },
    { text: "Provider can no longer access encrypted records", options: { bullet: true, breakLine: true } },
    { text: "AccessRevoked event is emitted for audit", options: { bullet: true } },
  ], { x: 5.5, y: 3.3, w: 3.4, h: 1.5, fontSize: 12, fontFace: "Calibri", color: C.inkSec });

  // ================================================================
  // SLIDE 8: Audit Trail
  // ================================================================
  let s8 = pres.addSlide();
  s8.background = { color: C.tealDeep };
  s8.addText("Immutable Audit Trail", {
    x: 0.8, y: 0.4, w: 8, h: 0.8,
    fontSize: 36, fontFace: "Georgia", bold: true, color: C.paper, margin: 0
  });
  s8.addText("Every action is permanently recorded on the blockchain. No one can alter or delete these logs.", {
    x: 0.8, y: 1.2, w: 8.4, h: 0.5,
    fontSize: 14, fontFace: "Calibri", color: C.tealLight
  });

  const events = [
    { name: "PatientRegistered", desc: "When a new patient signs up", color: C.teal },
    { name: "RecordUploaded", desc: "When an encrypted record is stored", color: C.sage },
    { name: "AccessGranted", desc: "When a patient shares access with a provider", color: "8B5CF6" },
    { name: "AccessRevoked", desc: "When a patient removes a provider's access", color: C.sienna },
  ];
  events.forEach((e, i) => {
    const y = 2.0 + i * 0.85;
    // Timeline dot
    s8.addShape(pres.shapes.OVAL, { x: 1.2, y: y + 0.15, w: 0.3, h: 0.3, fill: { color: e.color } });
    if (i < events.length - 1) {
      s8.addShape(pres.shapes.RECTANGLE, { x: 1.32, y: y + 0.45, w: 0.06, h: 0.55, fill: { color: C.teal, transparency: 50 } });
    }
    s8.addText(e.name, { x: 1.8, y: y + 0.02, w: 3.5, h: 0.35, fontSize: 15, fontFace: "Consolas", bold: true, color: C.paper, margin: 0 });
    s8.addText(e.desc, { x: 1.8, y: y + 0.38, w: 6, h: 0.3, fontSize: 12, fontFace: "Calibri", color: C.tealLight, margin: 0 });
  });

  // ================================================================
  // SLIDE 9: AHE-DHA Encryption Deep Dive
  // ================================================================
  let s9 = pres.addSlide();
  s9.background = { color: C.cream };
  s9.addText("AHE-DHA Encryption", {
    x: 0.8, y: 0.3, w: 8, h: 0.8,
    fontSize: 36, fontFace: "Georgia", bold: true, color: C.tealDeep, margin: 0
  });
  s9.addText("Adaptive Hybrid Encryption with Dynamic Hash Anchoring", {
    x: 0.8, y: 0.95, w: 8.4, h: 0.35,
    fontSize: 12, fontFace: "Calibri", italic: true, color: C.inkMuted
  });
  s9.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 1.3, w: 2.0, h: 0.05, fill: { color: C.sienna } });

  const components = [
    { title: "Sensitivity Score", desc: "Each field is weighted (diagnosis=1.0, age=0.3). Higher score means stricter encryption.", color: C.sienna },
    { title: "AES-256-GCM", desc: "A unique session key is generated for every single record. Provides fast, strong encryption.", color: C.teal },
    { title: "RSA Key Wrapping", desc: "The AES session key is encrypted with the patient's 2048-bit RSA public key.", color: C.tealDeep },
    { title: "Hash Anchors", desc: "SHA-256 hashes are chained with timestamps. Each record links to the previous one.", color: C.sage },
    { title: "Access Weights", desc: "W = 0.4(1-SS) + 0.35(role) + 0.25(regulation). Doctors get access, researchers may not.", color: "8B5CF6" },
  ];
  components.forEach((c, i) => {
    const col = i < 3 ? 0 : 1;
    const row = i < 3 ? i : i - 3;
    const x = 0.8 + col * 4.6;
    const y = 1.65 + row * 1.25;
    s9.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.2, h: 1.05, fill: { color: C.paper }, shadow: cardShadow() });
    s9.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.07, h: 1.05, fill: { color: c.color } });
    s9.addText(c.title, { x: x + 0.25, y: y + 0.08, w: 3.7, h: 0.35, fontSize: 14, fontFace: "Georgia", bold: true, color: C.ink, margin: 0 });
    s9.addText(c.desc, { x: x + 0.25, y: y + 0.45, w: 3.7, h: 0.5, fontSize: 11, fontFace: "Calibri", color: C.inkMuted, margin: 0 });
  });

  // ================================================================
  // SLIDE 10: Tech Stack
  // ================================================================
  let s10 = pres.addSlide();
  s10.background = { color: C.cream };
  s10.addText("Tech Stack", {
    x: 0.8, y: 0.4, w: 8, h: 0.8,
    fontSize: 36, fontFace: "Georgia", bold: true, color: C.tealDeep, margin: 0
  });
  s10.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 1.15, w: 1.0, h: 0.05, fill: { color: C.sienna } });

  const stack = [
    ["Blockchain", "Ethereum (Ganache local network)", C.tealDeep],
    ["Smart Contracts", "Solidity (PatientRegistry, EHRStorage, AccessControl)", C.teal],
    ["Encryption", "Python cryptography (AES-256-GCM + RSA-2048)", C.sienna],
    ["Backend", "Flask + web3.py", C.sage],
    ["Off-chain Storage", "Local filesystem (IPFS-ready)", C.teal],
    ["Frontend", "HTML / CSS / JavaScript", C.tealDeep],
    ["Wallet", "MetaMask browser extension", C.sienna],
    ["Dataset", "Kaggle Healthcare Dataset (pandas)", C.sage],
  ];

  stack.forEach((row, i) => {
    const y = 1.55 + i * 0.48;
    const bgColor = i % 2 === 0 ? C.paper : C.cream;
    s10.addShape(pres.shapes.RECTANGLE, { x: 0.8, y, w: 8.4, h: 0.44, fill: { color: bgColor } });
    s10.addShape(pres.shapes.RECTANGLE, { x: 0.8, y, w: 0.06, h: 0.44, fill: { color: row[2] } });
    s10.addText(row[0], { x: 1.1, y, w: 2.5, h: 0.44, fontSize: 13, fontFace: "Georgia", bold: true, color: C.ink, valign: "middle", margin: 0 });
    s10.addText(row[1], { x: 3.6, y, w: 5.4, h: 0.44, fontSize: 12, fontFace: "Calibri", color: C.inkSec, valign: "middle", margin: 0 });
  });

  // ================================================================
  // SLIDE 11: Performance Results
  // ================================================================
  let s11 = pres.addSlide();
  s11.background = { color: C.cream };
  s11.addText("Performance", {
    x: 0.8, y: 0.4, w: 8, h: 0.8,
    fontSize: 36, fontFace: "Georgia", bold: true, color: C.tealDeep, margin: 0
  });
  s11.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 1.15, w: 1.2, h: 0.05, fill: { color: C.sienna } });

  // Big stat callouts
  const stats = [
    { num: "0.04ms", label: "Encrypt per record", color: C.tealDeep },
    { num: "0.5ms", label: "Decrypt per record", color: C.sienna },
    { num: "~270K", label: "Gas per upload", color: C.sage },
    { num: "100%", label: "Hash integrity", color: C.teal },
  ];
  stats.forEach((st, i) => {
    const x = 0.5 + i * 2.35;
    s11.addShape(pres.shapes.RECTANGLE, { x, y: 1.7, w: 2.1, h: 1.8, fill: { color: C.paper }, shadow: cardShadow() });
    s11.addText(st.num, { x, y: 1.9, w: 2.1, h: 0.8, fontSize: 32, fontFace: "Georgia", bold: true, color: st.color, align: "center", valign: "middle" });
    s11.addText(st.label, { x, y: 2.75, w: 2.1, h: 0.5, fontSize: 12, fontFace: "Calibri", color: C.inkMuted, align: "center" });
  });

  // Table
  s11.addTable([
    [
      { text: "Metric", options: { fill: { color: C.tealDeep }, color: C.paper, bold: true, fontSize: 12, fontFace: "Calibri" } },
      { text: "Value", options: { fill: { color: C.tealDeep }, color: C.paper, bold: true, fontSize: 12, fontFace: "Calibri" } },
    ],
    ["Patient Registration Gas", "~157,000"],
    ["Record Upload Gas", "~272,000"],
    ["Grant Access Gas", "~105,000"],
    ["Revoke Access Gas", "~39,000"],
  ], {
    x: 0.8, y: 3.9, w: 8.4, h: 1.5,
    border: { pt: 0.5, color: C.inkMuted },
    fontSize: 12, fontFace: "Calibri", color: C.inkSec,
    colW: [4.2, 4.2],
    rowH: [0.32, 0.28, 0.28, 0.28, 0.28],
  });

  // ================================================================
  // SLIDE 12: Thank You
  // ================================================================
  let s12 = pres.addSlide();
  s12.background = { color: C.tealDeep };
  s12.addShape(pres.shapes.OVAL, { x: 6.5, y: -2, w: 6, h: 6, fill: { color: C.teal, transparency: 75 } });
  s12.addShape(pres.shapes.OVAL, { x: -2, y: 3, w: 5, h: 5, fill: { color: C.sienna, transparency: 80 } });

  s12.addText("Thank You", {
    x: 0.5, y: 1.5, w: 9, h: 1.2,
    fontSize: 52, fontFace: "Georgia", bold: true, color: C.paper, align: "center"
  });
  s12.addText("BlockMedChain — Securing Health Records, One Block at a Time", {
    x: 1.5, y: 3.0, w: 7, h: 0.6,
    fontSize: 16, fontFace: "Calibri", italic: true, color: C.tealLight, align: "center"
  });
  s12.addText("Questions?", {
    x: 3, y: 4.0, w: 4, h: 0.5,
    fontSize: 20, fontFace: "Georgia", color: C.sienna, align: "center"
  });

  // ---- Save ----
  await pres.writeFile({ fileName: "D:/BlockMedChain/BlockMedChain_Presentation.pptx" });
  console.log("Presentation saved to D:/BlockMedChain/BlockMedChain_Presentation.pptx");
}

main().catch(console.error);
