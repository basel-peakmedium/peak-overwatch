# 🚀 Deploy to Fly.io (Fix 45-90s Render Cold Starts)

## **Problem:** 
Render free/basic tier has 45-90 second cold starts. Basel reports: "The loading is abysmal" and "Can't demo with 90-second wait times."

## **Solution:** 
Migrate to **Fly.io** with 5-10 second cold starts on free tier.

## **Deployment Steps:**

### **1. Install Fly.io CLI**
```bash
curl -L https://fly.io/install.sh | sh
```

### **2. Login to Fly.io**
```bash
fly auth login
```

### **3. Create Fly.io App**
```bash
cd peak-overwatch
fly launch
```
- Use app name: `peak-overwatch`
- Region: `iad` (Washington DC - closest to Orlando)
- Yes to Postgres (optional for now)
- Yes to deploy now

### **4. Set Environment Variables**
```bash
fly secrets set SECRET_KEY=your-secret-key-here
```

### **5. Deploy**
```bash
fly deploy
```

### **6. Set Custom Domain**
```bash
fly certs create app.peakoverwatch.com
```

## **Expected Results:**
- **Load Time:** 5-10 seconds (vs 45-90s on Render)
- **Cost:** Free tier available
- **Performance:** Demo-viable
- **Custom Domain:** `app.peakoverwatch.com` working fast

## **Why Fly.io is Better:**
- **Faster cold starts:** 5-10s vs 45-90s
- **Better free tier:** 3 shared VMs, 3GB storage
- **Global network:** 30+ regions
- **Postgres included:** Free 1GB database

## **Post-Migration:**
1. Update DNS records in Cloudflare
2. Test login/dashboard performance
3. Record demo video (now possible)

## **Rollback Plan:**
If issues occur, Render deployment remains at:
- `https://peak-overwatch.onrender.com`
- Can switch back anytime