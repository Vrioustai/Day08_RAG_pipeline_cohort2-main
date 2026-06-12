# Quick Deployment Checklist for Railway

## 🚂 Pre-Deployment (Local)

### 1. Code & Files
- [ ] `.env` file exists locally with all API keys
- [ ] `.env` is in `.gitignore` (NOT in git)
- [ ] `Procfile` exists with correct Streamlit command
- [ ] `railway.toml` exists (optional but recommended)
- [ ] `requirements.txt` is up-to-date: `pip freeze > requirements.txt`

### 2. Test Locally
```bash
# Run the app locally to verify
streamlit run app.py

# Should see:
# - App loading without errors
# - All API keys working
# - Chatbot responsive
```

### 3. Validation Script
```bash
python check_deployment.py
# All checks should be ✅
```

### 4. Commit & Push
```bash
git add Procfile railway.toml requirements.txt DEPLOYMENT_RAILWAY.md
git commit -m "Add Railway deployment files"
git push origin main
```

---

## 🌐 On Railway Dashboard

### 5. Create Project
- [ ] Login to railway.app
- [ ] Click "New Project"
- [ ] Select "Deploy from GitHub repo"
- [ ] Choose this repository

### 6. Set Environment Variables
Go to **Project → Variables** and add:

```
OPENAI_API_KEY = <your-key>
JINA_API_KEY = <your-key>
PAGEINDEX_API_KEY = <your-key>
WEAVIATE_URL = <your-url> (if using Weaviate Cloud)
WEAVIATE_API_KEY = <your-key> (if using Weaviate Cloud)
```

### 7. Deploy
- [ ] Click "Deploy" button (or auto-deploy on push)
- [ ] Wait for build to complete (3-5 min)
- [ ] Check logs for errors

### 8. Verify
- [ ] Check "Deployments" section - status should be "Success"
- [ ] Click the Railway URL to open your app
- [ ] Test the chatbot works

---

## 🔍 Post-Deployment Checks

- [ ] App loads in browser (no 500 errors)
- [ ] Streamlit interface visible
- [ ] Chatbot can process queries
- [ ] All tabs/pages working
- [ ] No API key errors in logs

---

## 📊 View Logs & Monitoring

**To debug issues:**
```
Railway Dashboard → Project → Deployments → Your Latest Deploy → Logs
```

**Common issues & solutions:**
| Issue | Solution |
|-------|----------|
| "Module not found" | Update `requirements.txt` |
| "API key error" | Check variable names in Railway |
| "Timeout" | Check data loading, increase RAM |
| "Memory exceeded" | Upgrade Railway plan |
| "Port already in use" | Railway auto-assigns port |

---

## 🎯 Success Criteria

✅ You're done when:
- Railway shows "Success" in Deployments
- App URL works in browser
- Chatbot responds to queries
- No errors in Logs section
- Health check passing

---

## 🚀 Auto-Deployment Setup (Optional)

Railway auto-deploys when you push to `main`:
```bash
# Enable auto-deploy
# 1. On Railway: Settings → Auto-Deploy Enabled ✅
# 2. Push to trigger deploy:
git add .
git commit -m "Update"
git push origin main
```

---

## 📞 Support Resources

- Railway Docs: https://docs.railway.app
- Streamlit Docs: https://docs.streamlit.io
- GitHub Issues: Your repository issues tab
- Railway Discord: https://discord.gg/railway

---

**Status:** Ready for deployment ✅
**Created:** 2024
