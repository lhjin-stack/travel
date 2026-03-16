require('dotenv').config();
const express = require('express');
const session = require('express-session');
const passport = require('passport');
const { Strategy: GoogleStrategy } = require('passport-google-oauth20');
const path = require('path');
const geoip = require('geoip-lite');

function detectLang(req) {
  const ip = req.headers['x-forwarded-for']?.split(',')[0].trim() || req.socket.remoteAddress || '';
  const cleanIp = ip.replace(/^::ffff:/, '');
  const geo = geoip.lookup(cleanIp);
  const country = geo?.country || '';
  if (country === 'KR') return 'ko';
  if (['CN', 'HK', 'MO', 'TW'].includes(country)) return 'zh';
  // 로컬(127.0.0.1) 또는 감지 실패 시 Accept-Language 헤더로 폴백
  const accept = (req.headers['accept-language'] || '').toLowerCase();
  if (accept.startsWith('ko')) return 'ko';
  if (accept.startsWith('zh')) return 'zh';
  return 'en';
}

const app = express();
const PORT = process.env.PORT || 3000;
const ALLOWED_DOMAIN = 'ekmtc.com';

// ── Passport ──────────────────────────────────────────────
passport.use(new GoogleStrategy({
  clientID:     process.env.GOOGLE_CLIENT_ID,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  callbackURL:  process.env.CALLBACK_URL || `http://localhost:${PORT}/auth/google/callback`,
}, (accessToken, refreshToken, profile, done) => {
  const email = (profile.emails?.[0]?.value || '').toLowerCase();
  if (!email.endsWith(`@${ALLOWED_DOMAIN}`)) {
    return done(null, false, { message: `@${ALLOWED_DOMAIN} 계정만 접근 가능합니다.` });
  }
  return done(null, { id: profile.id, name: profile.displayName, email });
}));

passport.serializeUser((user, done) => done(null, user));
passport.deserializeUser((user, done) => done(null, user));

// ── Session (쿠키 maxAge 없음 = 브라우저 종료 시 소멸) ──────
app.use(session({
  secret: process.env.SESSION_SECRET || 'kmtc-iran-policy-secret-change-me',
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    // maxAge 미설정 → 세션 쿠키, 브라우저 창 종료 시 자동 소멸
  },
}));

app.use(passport.initialize());
app.use(passport.session());

// ── Auth middleware ────────────────────────────────────────
function requireAuth(req, res, next) {
  if (req.isAuthenticated()) return next();
  req.session.returnTo = req.originalUrl;
  res.redirect('/login');
}

// ── Routes ────────────────────────────────────────────────
app.get('/login', (req, res) => {
  const error = req.query.error || '';
  const lang = detectLang(req);
  res.send(`<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KMTC Login</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
      background: linear-gradient(135deg, #002244 0%, #003f7f 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .card {
      background: #fff;
      border-radius: 14px;
      padding: 36px 36px 28px;
      width: 360px;
      text-align: center;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    .logo { font-size: 36px; margin-bottom: 8px; }
    h1 { font-size: 17px; font-weight: 700; color: #003366; margin-bottom: 4px; }
    .sub { font-size: 12px; color: #6b7280; margin-bottom: 24px; line-height: 1.6; }
    .lang-bar {
      display: flex;
      justify-content: center;
      gap: 6px;
      margin-bottom: 20px;
    }
    .lb {
      background: none;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      padding: 4px 12px;
      font-size: 12px;
      cursor: pointer;
      color: #374151;
      transition: all .15s;
    }
    .lb.active { background: #003366; color: #fff; border-color: #003366; font-weight: 600; }
    .google-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      background: #fff;
      border: 1.5px solid #dadce0;
      border-radius: 8px;
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 600;
      color: #3c4043;
      cursor: pointer;
      text-decoration: none;
      width: 100%;
      transition: background .15s, box-shadow .15s;
    }
    .google-btn:hover { background: #f8f9fa; box-shadow: 0 2px 8px rgba(0,0,0,0.12); }
    .google-icon { width: 20px; height: 20px; flex-shrink: 0; }
    .notice {
      margin-top: 16px;
      font-size: 11px;
      color: #9ca3af;
      background: #f9fafb;
      border-radius: 6px;
      padding: 8px 12px;
      line-height: 1.6;
    }
    .error {
      margin-bottom: 16px;
      font-size: 12px;
      color: #c00;
      background: #fff5f5;
      border: 1px solid #fca5a5;
      border-radius: 6px;
      padding: 8px 12px;
    }
    [data-t] { display: none; }
    .ko [data-t="ko"], .en [data-t="en"], .zh [data-t="zh"] { display: inline; }
    .ko [data-tb="ko"], .en [data-tb="en"], .zh [data-tb="zh"] { display: block; }
    [data-tb] { display: none; }
  </style>
</head>
<body>
  <div class="card ${lang}" id="card">
    <div class="logo">⚓</div>
    <h1>
      <span data-t="ko">KMTC 미·이란 전쟁 정책 안내</span>
      <span data-t="en">KMTC US-Iran War Policy</span>
      <span data-t="zh">KMTC 美伊战争政策指引</span>
    </h1>
    <p class="sub">
      <span data-t="ko">대외비 내부 자료입니다.<br>@ekmtc.com 구글 계정으로만 접근 가능합니다.</span>
      <span data-t="en">Confidential internal document.<br>Access restricted to @ekmtc.com Google accounts only.</span>
      <span data-t="zh">本文件为内部机密资料。<br>仅限 @ekmtc.com 谷歌账号访问。</span>
    </p>

    <div class="lang-bar">
      <button class="lb ${lang==='ko'?'active':''}" onclick="setLang('ko',this)">한국어</button>
      <button class="lb ${lang==='en'?'active':''}" onclick="setLang('en',this)">English</button>
      <button class="lb ${lang==='zh'?'active':''}" onclick="setLang('zh',this)">中文</button>
    </div>

    ${error ? `<div class="error">⛔ ${error}</div>` : ''}

    <a href="/auth/google" class="google-btn">
      <svg class="google-icon" viewBox="0 0 48 48">
        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
      </svg>
      <span data-t="ko">Google 계정으로 로그인</span>
      <span data-t="en">Sign in with Google</span>
      <span data-t="zh">使用 Google 账号登录</span>
    </a>

    <div class="notice">
      <span data-t="ko">🔒 @ekmtc.com 계정 필수 · 창 종료 시 자동 로그아웃</span>
      <span data-t="en">🔒 @ekmtc.com accounts only · Auto logout on window close</span>
      <span data-t="zh">🔒 仅限 @ekmtc.com 账号 · 关闭窗口自动退出</span>
    </div>
  </div>
  <script>
    function setLang(lang, btn) {
      document.getElementById('card').className = 'card ' + lang;
      document.querySelectorAll('.lb').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }
  </script>
</body>
</html>`);
});

app.get('/auth/google', passport.authenticate('google', {
  scope: ['profile', 'email'],
  hd: ALLOWED_DOMAIN,   // Google 계정 선택 화면에서 ekmtc.com만 표시
  prompt: 'select_account',
}));

app.get('/auth/google/callback',
  passport.authenticate('google', {
    failureRedirect: '/login?error=' + encodeURIComponent('@ekmtc.com 계정이 아닙니다.'),
  }),
  (req, res) => {
    const returnTo = req.session.returnTo || '/';
    delete req.session.returnTo;
    res.redirect(returnTo);
  }
);

app.get('/logout', (req, res) => {
  req.logout(() => {
    req.session.destroy();
    res.redirect('/login');
  });
});

// ── Protected: 메인 정책 페이지 ──────────────────────────
app.get('/', requireAuth, (req, res) => {
  res.sendFile(path.join(__dirname, 'weekly-report', 'iran-war-policy.html'));
});

// ── 404 ───────────────────────────────────────────────────
app.use((req, res) => res.status(404).send('Not found'));

app.listen(PORT, () => {
  console.log(`✅ Server running: http://localhost:${PORT}`);
  console.log(`   Domain restriction: @${ALLOWED_DOMAIN}`);
});
