# 🚂 Deployment Guide: Railway

Hướng dẫn chi tiết để deploy dự án RAG Chatbot lên Railway.

---

## 📋 Yêu Cầu Trước Deployment

### 1. Chuẩn Bị
- ✅ Tài khoản Railway (railway.app)
- ✅ Git repository (GitHub, GitLab, hoặc Gitea)
- ✅ Tất cả API keys cần thiết
- ✅ Python 3.9+ (local testing)

### 2. API Keys Cần Thiết
Chuẩn bị các environment variables sau:

```
OPENAI_API_KEY=sk-proj-xxxxx              # OpenAI API key
JINA_API_KEY=jina_xxxxx                   # Jina AI (reranking)
PAGEINDEX_API_KEY=xxxxx                   # PageIndex API
WEAVIATE_URL=https://xxx.weaviate.network # Weaviate Cloud URL (nếu dùng)
WEAVIATE_API_KEY=xxxxx                    # Weaviate API key (nếu dùng)
```

---

## 🚀 Deployment Steps

### Bước 1: Chuẩn Bị Repository

```bash
# 1. Đảm bảo .env không được commit
git status
# Kiểm tra .env nằm trong .gitignore

# 2. Đẩy code lên GitHub (nếu chưa)
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### Bước 2: Tạo Project Trên Railway

1. **Truy cập Railway**: https://railway.app
2. **Đăng nhập** hoặc **Tạo tài khoản mới**
3. **Click "New Project"** → **"Deploy from GitHub repo"**
4. **Chọn repository** của dự án
5. **Cấp quyền** để Railway access GitHub

### Bước 3: Cấu Hình Environment Variables

1. Vào **Project** → **Variables**
2. Thêm tất cả API keys:

```
OPENAI_API_KEY = sk-proj-xxxxx
JINA_API_KEY = jina_xxxxx
PAGEINDEX_API_KEY = xxxxx
WEAVIATE_URL = https://xxx.weaviate.network
WEAVIATE_API_KEY = xxxxx
```

3. **Click "Add"** để lưu từng variable

### Bước 4: Kiểm Tra Cấu Hình

Railway sẽ tự động detect:
- ✅ `Procfile` → Start command cho Streamlit
- ✅ `requirements.txt` → Dependencies
- ✅ `railway.toml` → Cấu hình thêm (optional)

### Bước 5: Deploy

1. Mặc định Railway sẽ **tự động deploy** khi có push mới
2. Hoặc **Manual deploy**: Click **"Deploy"** button
3. Chờ build process hoàn thành (3-5 phút)

### Bước 6: Kiểm Tra Logs

```
Deployment → Logs
```

Tìm dòng:
```
Collecting usage statistics. To deactivate, set browser.gatherUsageStats to false.
...
  You can now view your Streamlit app in your browser.
  URL: https://your-project-railway.app
```

---

## 🔧 Troubleshooting

### ❌ "Module not found" error
**Giải pháp:**
```bash
# Cập nhật requirements.txt
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push
```

### ❌ "Streamlit not loading" / Timeout
**Giải pháp:**
1. Kiểm tra `Procfile` đúng cú pháp
2. Tăng timeout trong `railway.toml`:
```toml
[deploy]
healthcheckPath = "/"
healthcheckTimeout = 100
```

### ❌ "Memory exceeded" / Crash
**Giải pháp:**
1. Upgrade Railway plan → More RAM
2. Hoặc optimize data loading:
```python
# app.py
@st.cache_resource
def load_vector_db():
    # Load once, reuse across sessions
    return initialize_chroma_db()
```

### ❌ "API Key not working"
**Giải pháp:**
```python
# app.py - Debug
import os
print(f"OPENAI_API_KEY exists: {'OPENAI_API_KEY' in os.environ}")
```

---

## 📊 Monitoring & Maintenance

### Xem Logs
```
Railway Dashboard → Project → Deployments → Logs
```

### Auto-Restart (Enabled by default)
Railway tự động restart nếu app crash.

### Health Checks
Railway ping app mỗi 30s. Nếu health check fail 5 lần → restart.

### Scale Up
Nếu cần performance tốt hơn:
1. **Railway Dashboard** → **Settings**
2. **Increase RAM/CPU** → Deploy lại

---

## 🌐 Custom Domain (Optional)

1. **Railway Dashboard** → **Settings** → **Domains**
2. **Add Custom Domain**
3. **Configure DNS** tại domain provider (A record hoặc CNAME)
4. **Verify domain** sau 24-48 giờ

---

## 📝 Important Notes

### Data Persistence
- ⚠️ Railway containers là ephemeral (tạm thời)
- Dữ liệu local sẽ bị xóa khi deploy lại
- **Giải pháp**: 
  - Dùng persistent storage (Railway Disk)
  - Hoặc lưu vectors trên Weaviate Cloud / Chroma Cloud

### Environment Variables
- ✅ Không commit `.env` file
- ✅ Set tất cả sensitive keys trên Railway dashboard
- ✅ App sẽ load từ Railway environment

### Build Time
- Lần build đầu: 5-10 phút (install dependencies)
- Build tiếp theo: 1-2 phút (cache)

---

## ✨ Advanced: CI/CD Pipeline (Optional)

Tự động test trước khi deploy:

```yaml
# .github/workflows/railway-deploy.yml
name: Railway Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: |
          pip install -r requirements.txt
          pytest tests/ -v
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: railwayapp/railway-action@v1
        with:
          token: ${{ secrets.RAILWAY_TOKEN }}
```

---

## 🎯 Verification Checklist

- [ ] Repository on GitHub (public hoặc Railway có access)
- [ ] `Procfile` đúng cú pháp
- [ ] `requirements.txt` có tất cả dependencies
- [ ] `.env` nằm trong `.gitignore`
- [ ] Tất cả API keys set trên Railway
- [ ] `railroad.toml` configured (optional)
- [ ] Local test: `streamlit run app.py` chạy ok
- [ ] First deploy successful & logs clean
- [ ] App loads trong browser
- [ ] Chatbot có thể respond

---

## 📚 Tài Liệu Tham Khảo

- [Railway Docs](https://docs.railway.app)
- [Streamlit Deployment Guide](https://docs.streamlit.io/deploy/streamlit-community-cloud)
- [Python on Railway](https://docs.railway.app/guides/python)
- [Environment Variables](https://docs.railway.app/reference/environment-variables)

---

**Last Updated:** 2024-06
**Status:** Ready for Deployment ✅
