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
- **Real-Time Push Notifications**: Instant alerts when new tenders are scraped

## Technical Architecture
- **Frontend**: Expo/React Native (web + mobile)
- **Backend**: FastAPI with MongoDB
- **Scraping**: Playwright for JavaScript-heavy sites, aiohttp/BeautifulSoup for static
- **Push Notifications**: Expo Push Service with backend integration

## What's Been Implemented

### February 23, 2026 - Robustness, Scraper Fixes & Push Notifications

#### Completed
1. **Backend Optimizations for Concurrent Users**
   - MongoDB connection pooling (50 max, 10 min connections)
   - Database indexes on frequently queried fields
   - API pagination (default 1000, max 5000)
   - In-memory caching for users and stats endpoints
   - Rate limiting on API endpoints
   - Health check (`/api/health`) and stats (`/api/stats`) endpoints

2. **Scraper Fixes**
   - Fixed simap.ch scraper to use current portal (not archive)
   - Added strict 2026+ date filtering for Swiss tenders
   - Deleted 31 old tenders from database (before 2026)
   - All tenders now show valid 2026+ deadlines

3. **Real-Time Push Notifications**
   - Backend: Push token registration/unregistration endpoints
   - Backend: `send_push_notifications()` function using Expo Push Service
   - Backend: Auto-notify users when new tenders are scraped
   - Frontend: NotificationContext for handling notifications
   - Frontend: notifications.ts service for token management
   - Integration: Scraper triggers push notifications for new tenders

4. **Developer Projects Feature Enhanced**
   - 19 realistic German developer projects
   - Coverage: NRW (8), Brandenburg (7), Berlin (3)
   - Timeline visualization with phase progress

5. **Bug Fixes**
   - Fixed API URL resolution for web builds
   - Fixed login button click handling
   - Fixed users API (handle missing `created_at` field)

### Previous Sessions
- Playwright-based TED Europa scraper
- CPV code search functionality
- Multi-select filters with dynamic counts
- "Shared with me" feature
- Conditional share button based on `can_share` permission
- WhatsApp sharing option

## Push Notification API Endpoints
- `POST /api/push-tokens` - Register push token
- `DELETE /api/push-tokens/{user_id}` - Unregister tokens (logout)
- `GET /api/push-tokens/status` - Get notification status
- `POST /api/notifications/send` - Send notifications (admin)
- `POST /api/notifications/test` - Test notification

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
- Tenders: ~3677 (all 2026+)
- Users: 10
- Developer Projects: 19

## Key Files
- `/app/backend/server.py` - Main API with push notifications
- `/app/backend/comprehensive_scraper.py` - Playwright TED scraper
- `/app/backend/developer_scraper.py` - Developer projects
- `/app/frontend/services/notifications.ts` - Push notification service
- `/app/frontend/contexts/NotificationContext.tsx` - Notification state
- `/app/frontend/app/(tabs)/index.tsx` - Main tender list

## Remaining Tasks

### P1 - High Priority
- [ ] UI for Tender "Claim" and "Chat" features
- [ ] Notification settings UI in profile page

### P2 - Medium Priority  
- [ ] Real scraper for Market News section
- [ ] ESLint configuration fix for TypeScript

### P3 - Low Priority
- [ ] Frontend linting error in index.tsx

## Known Limitations
- Push notifications require physical device or Expo Go app (won't work on web preview)
- Developer project scraping relies on seed data
- simap.ch scraper may need periodic URL updates
