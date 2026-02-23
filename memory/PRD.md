# GroVELLOWS - German Construction Tender Tracking App

## Original Problem Statement
Build a mobile app "GroVELLOWS" for tracking tender updates from German and Swiss construction tender platforms.

## Core Features
- **Tender Tracking**: Scrape and display construction tenders from German/Swiss platforms
- **Multi-Select Filters**: Filter by typology, service, country with dynamic tender counts
- **Developer Projects**: Track German property developer project announcements
- **Team Collaboration**: Share tenders with team members, "Shared with me" section
- **User Permissions**: Granular `can_share` flag for sharing rights
- **International Tenders**: CPV-based search across European countries via TED portal

## Technical Architecture
- **Frontend**: Expo/React Native (web + mobile)
- **Backend**: FastAPI with MongoDB
- **Scraping**: Playwright for JavaScript-heavy sites, aiohttp/BeautifulSoup for static

## What's Been Implemented

### December 2025 - Robustness & Developer Projects Session

#### Completed
1. **Backend Optimizations for Concurrent Users**
   - Added MongoDB connection pooling (50 max, 10 min connections)
   - Created database indexes on frequently queried fields (country, category, building_typology, etc.)
   - Implemented pagination for tenders API (limit/skip params)
   - Added in-memory caching for users and stats endpoints
   - Added rate limiting on API endpoints
   - Created health check (`/api/health`) and stats (`/api/stats`) endpoints

2. **Developer Projects Feature**
   - Enhanced seed data with 19 realistic German developer projects
   - Projects from major developers: GEWOBAG, HOWOGE, Vonovia, Pandion, HOCHTIEF, etc.
   - Coverage: NRW (8), Brandenburg (7), Berlin (3), Other (1)
   - Timeline visualization with phase progress

3. **Frontend Stability**
   - Fixed expo web mode (switched from --tunnel to --web)
   - Fixed login button click handling (Pressable with accessibilityRole)
   - Maintained Platform.select for shadow styles

4. **Database Updates**
   - Fixed users API (handle missing `created_at` field)
   - Updated user sharing permissions as per requirements

### Previous Sessions
- Playwright-based TED Europa scraper
- CPV code search functionality
- Multi-select filters with dynamic counts
- "Shared with me" feature
- Conditional share button based on `can_share` permission
- WhatsApp sharing option

## Test Credentials
| Email | Password | Role | Can Share |
|-------|----------|------|-----------|
| director@grovellows.de | Director123 | Director | Yes |
| stephan.hintzen@grovellows.de | Stephan123 | Partner | Yes |
| jurgen.volm@grovellows.de | Jurgen123 | Partner | Yes |
| parth.sheth@grovellows.de | Parth123 | Project Manager | Yes |
| phillip.kanthack@grovellows.de | Phillip123 | Project Manager | Yes |
| vesna.udovcic@grovellows.de | Vesna123 | Admin | No |

## Database Stats
- Tenders: ~3700
- Users: 10
- Developer Projects: 19

## Key Files
- `/app/backend/server.py` - Main API with optimizations
- `/app/backend/comprehensive_scraper.py` - Playwright TED scraper
- `/app/backend/developer_scraper.py` - Developer projects scraper + seed data
- `/app/frontend/app/(tabs)/index.tsx` - Main tender list with filters
- `/app/frontend/app/(tabs)/projects.tsx` - Developer projects UI

## Remaining Tasks

### P1 - High Priority
- [ ] Push notification frontend implementation
- [ ] UI for Tender "Claim" and "Chat" features

### P2 - Medium Priority
- [ ] Real scraper for Market News section
- [ ] ESLint configuration fix for TypeScript

### P3 - Low Priority
- [ ] Frontend linting error in index.tsx (`interface` keyword reserved)

## Known Limitations
- Developer project scraping relies on seed data (most developer websites block scraping)
- ngrok tunnel can be unstable (expo runs in --web mode as fallback)
