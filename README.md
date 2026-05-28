# pixel-mcp

Serveur MCP (Model Context Protocol) pour la **Pixel Watch** et toute donnée santé synchronisée via Google Health Connect, à travers la nouvelle **Google Health API v4** (qui remplace l'ancienne Fitbit Web API, dépréciée en septembre 2026).

Conçu pour brancher Claude (Desktop ou Code) sur ses données santé : coaching basé sur la charge réelle, conseils nutrition selon le sommeil/HRV, suivi récup, etc.

Couvre toute la surface de l'API :
- **Activité** — pas, distance, étages, énergie active, AZM, niveau d'activité, séances d'exercice (depuis Pixel Watch, Garmin Connect, Strava… via Health Connect)
- **Cardio** — FC live, FC repos, zones HR, HRV nocturne et intraday, VO2max (général + course)
- **Sommeil** — sessions complètes avec phases, dérives de température cutanée
- **Wellness** — SpO2 (nuit + résumé), fréquence respiratoire, température corporelle
- **Corps** — poids, masse grasse, taille, glycémie
- **Nutrition** — food log, hydratation
- **Cardiaque événementiel** — ECG, notifications de rythme irrégulier (IRN)
- **Natation** — détail par longueur
- **Profil & paramètres** — lecture et écriture

## Pourquoi ce projet

L'API Google Health v4 est très récente, mal documentée à plusieurs endroits (filtres AIP-160 entre snake_case/camelCase, structures `sample_time.physical_time` nestées, exercise qui exige `civil_start_time` au lieu de `start_time`…). Ce repo encapsule tous ces pièges derrière 49 tools MCP propres et prêts à l'emploi.

## Setup

### 1. Projet Google Cloud + Health API

1. Va sur https://console.cloud.google.com et crée un nouveau projet (ex: `pixel-mcp`).
2. Active l'API : https://console.developers.google.com/apis/library/health.googleapis.com → **Enable**.
3. **OAuth consent screen** : type "External", remplis nom + email. Dans **Audience**, ajoute ton email Google (de la Pixel Watch) comme **Test user**.
4. **Data Access (scopes)** : https://console.developers.google.com/auth/scopes — ajoute tous les scopes `googlehealth.*` (readonly + writeonly) que tu veux utiliser. Pour tout couvrir : 15 scopes (activity_and_fitness, ecg, health_metrics, irn, location, nutrition, profile, settings, sleep — read et write).
5. **Credentials** : https://console.developers.google.com/apis/credentials → **Create credentials → OAuth client ID** :
   - Application type : **Web application**
   - Name : `pixel-mcp`
   - **Authorized redirect URIs** : `http://127.0.0.1:8733/callback`
   - Crée → note **Client ID** et **Client Secret**.

### 2. .env

```
GOOGLE_HEALTH_CLIENT_ID=...
GOOGLE_HEALTH_CLIENT_SECRET=...
```

### 3. Installer & autoriser

```bash
git clone https://github.com/<ton-user>/pixel-mcp.git ~/pixel-mcp
cd ~/pixel-mcp
cp .env.example .env   # remplis GOOGLE_HEALTH_CLIENT_ID/SECRET
uv sync
uv run python -c "from pixel_mcp.auth import TokenManager; TokenManager().ensure_authorized()"
```

Le navigateur s'ouvre, tu cliques **Autoriser**. Tokens dans `~/.config/pixel-mcp/tokens.json` (chmod 600).

### 4. Brancher sur Claude Code

```bash
claude mcp add pixel -- uv --directory ~/pixel-mcp run python -m pixel_mcp.server
```

## Architecture

L'API Google Health v4 expose une seule resource générique `users/me/dataTypes/{type}/dataPoints`. Le MCP fournit :

- **`tools/users.py`** — identité, profil, settings, IRN profile (get/update).
- **`tools/devices.py`** — appareils appairés (Pixel Watch, etc.).
- **`tools/datapoints.py`** — opérations brutes : list/get/create/patch/batchDelete/rollUp/dailyRollUp/reconcile/exportTcx sur n'importe quel data type.
- **`tools/convenience.py`** — wrappers haut-niveau par domaine (get_steps, get_heart_rate, get_sleep, get_hrv, get_spo2…) qui construisent les filtres AIP-160 pour toi.

49 tools au total. Pour des cas non couverts par les wrappers, utilise `list_data_points(data_type, filter=...)` directement.
