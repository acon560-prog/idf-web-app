const express = require("express");
const jwt = require("jsonwebtoken");
const bcrypt = require("bcryptjs");
const { ObjectId } = require("mongodb");

const router = express.Router();

const ACCESS_EXPIRES_IN = process.env.JWT_ACCESS_TOKEN_EXPIRES || "1h";
const REFRESH_EXPIRES_IN = process.env.JWT_REFRESH_TOKEN_EXPIRES || "30d";
const JWT_SECRET = process.env.JWT_SECRET_KEY || process.env.JWT_SECRET || "change-me";
const ADMIN_EMAIL = (process.env.ADMIN_EMAIL || "").trim().toLowerCase();

function normalizeEmail(email) {
  return typeof email === "string" ? email.trim().toLowerCase() : "";
}

function determineRole(userDoc) {
  const email = normalizeEmail(userDoc?.email);
  if (email && ADMIN_EMAIL && email === ADMIN_EMAIL) return "admin";
  return userDoc?.role || "user";
}

function serializeUser(userDoc) {
  if (!userDoc) return null;
  const role = determineRole(userDoc);
  return {
    id: String(userDoc._id),
    email: userDoc.email || null,
    name: userDoc.name || "",
    subscriptionStatus: userDoc.subscriptionStatus || "trialing",
    plan: userDoc.plan || null,
    trialStartsAt: userDoc.trialStartsAt ? new Date(userDoc.trialStartsAt).toISOString() : null,
    trialEndsAt: userDoc.trialEndsAt ? new Date(userDoc.trialEndsAt).toISOString() : null,
    stripeCustomerId: userDoc.stripeCustomerId || null,
    role,
  };
}

function signAccessToken(userDoc) {
  const role = determineRole(userDoc);
  return jwt.sign(
    {
      type: "access",
      email: userDoc.email || null,
      subscriptionStatus: userDoc.subscriptionStatus || "trialing",
      role,
    },
    JWT_SECRET,
    {
      subject: String(userDoc._id),
      expiresIn: ACCESS_EXPIRES_IN,
    },
  );
}

function signRefreshToken(userDoc) {
  return jwt.sign(
    { type: "refresh" },
    JWT_SECRET,
    {
      subject: String(userDoc._id),
      expiresIn: REFRESH_EXPIRES_IN,
    },
  );
}

function parseBearerToken(req) {
  const header = req.headers.authorization || "";
  const match = String(header).match(/^Bearer\s+(.+)$/i);
  return match ? match[1] : null;
}

function requireJwt(expectedType) {
  return (req, res, next) => {
    const token = parseBearerToken(req);
    if (!token) return res.status(401).json({ error: "Missing bearer token." });
    try {
      const payload = jwt.verify(token, JWT_SECRET);
      if (expectedType && payload?.type !== expectedType) {
        return res.status(401).json({ error: "Invalid token type." });
      }
      req.auth = { payload, token, userId: payload?.sub };
      return next();
    } catch (_err) {
      return res.status(401).json({ error: "Invalid or expired token." });
    }
  };
}

router.post("/register", async (req, res) => {
  const payload = req.body || {};
  const email = normalizeEmail(payload.email);
  const username = typeof payload.username === "string" ? payload.username.trim() : "";
  const password = payload.password;
  const name = typeof payload.name === "string" ? payload.name.trim() : "";

  if (!password) return res.status(400).json({ error: "Password is required." });
  if (!email && !username) {
    return res.status(400).json({ error: "An email or username is required." });
  }

  const users = req.db.collection("users");

  if (email) {
    const exists = await users.findOne({ email });
    if (exists) return res.status(409).json({ error: "An account with this email already exists." });
  }
  if (username) {
    const exists = await users.findOne({ username });
    if (exists) return res.status(409).json({ error: "An account with this username already exists." });
  }

  const now = new Date();
  const trialEndsAt = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
  const role = email && ADMIN_EMAIL && email === ADMIN_EMAIL ? "admin" : "user";

  const passwordHash = await bcrypt.hash(String(password), 10);
  const userDoc = {
    email: email || null,
    username: username || null,
    name,
    passwordHash,
    subscriptionStatus: "trialing",
    plan: null,
    stripeCustomerId: null,
    trialStartsAt: now,
    trialEndsAt,
    createdAt: now,
    updatedAt: now,
    role,
  };

  const result = await users.insertOne(userDoc);
  userDoc._id = result.insertedId;

  return res.status(201).json({
    user: serializeUser(userDoc),
    accessToken: signAccessToken(userDoc),
    refreshToken: signRefreshToken(userDoc),
  });
});

router.post("/login", async (req, res) => {
  const payload = req.body || {};
  const identifier = payload.email || payload.username;
  const password = payload.password;

  if (!identifier || !password) {
    return res.status(400).json({ error: "Email/username and password are required." });
  }

  const users = req.db.collection("users");
  const identifierStr = String(identifier).trim();
  const email = identifierStr.includes("@") ? normalizeEmail(identifierStr) : "";

  const userDoc = await users.findOne(email ? { email } : { username: identifierStr });
  if (!userDoc || !userDoc.passwordHash) return res.status(401).json({ error: "Invalid credentials." });

  const ok = await bcrypt.compare(String(password), String(userDoc.passwordHash));
  if (!ok) return res.status(401).json({ error: "Invalid email or password." });

  const role = determineRole(userDoc);
  await users.updateOne(
    { _id: userDoc._id },
    { $set: { updatedAt: new Date(), role } },
  );
  userDoc.role = role;

  return res.json({
    user: serializeUser(userDoc),
    accessToken: signAccessToken(userDoc),
    refreshToken: signRefreshToken(userDoc),
  });
});

router.get("/me", requireJwt("access"), async (req, res) => {
  const users = req.db.collection("users");
  let objectId;
  try {
    objectId = req.auth.userId ? new ObjectId(req.auth.userId) : null;
  } catch {
    objectId = null;
  }
  const userDoc = await users.findOne({ _id: objectId }).catch(() => null);
  if (!userDoc) return res.status(404).json({ error: "User not found." });
  return res.json({ user: serializeUser(userDoc) });
});

router.post("/refresh-token", requireJwt("refresh"), async (req, res) => {
  const users = req.db.collection("users");
  let objectId;
  try {
    objectId = req.auth.userId ? new ObjectId(req.auth.userId) : null;
  } catch {
    objectId = null;
  }
  const userDoc = await users.findOne({ _id: objectId }).catch(() => null);
  if (!userDoc) return res.status(404).json({ error: "User not found." });
  return res.json({ accessToken: signAccessToken(userDoc) });
});

module.exports = router;
