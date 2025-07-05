## 📄 **2. Documentation API** (`docs/API.md`)

```markdown
# 🔌 Documentation API - Smart Route

API RESTful pour l'optimisation intelligente d'itinéraires.

## 📋 Vue d'ensemble

**Base URL**: `https://api.smartroute.com/api`  
**Version**: v1  
**Format**: JSON  
**Authentification**: Session-based (Google OAuth)  
**Rate Limiting**: 100 requêtes/heure (1000 pour utilisateurs authentifiés)

---

## 🔐 Authentification

### Google OAuth Login
```http
POST /auth/login