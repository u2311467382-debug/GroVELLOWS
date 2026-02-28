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
- **Tender Claim & Chat**: Team members can claim tenders and discuss via chat

## Technical Architecture
- **Frontend**: Expo/React Native (web + mobile)
- **Backend**: FastAPI with MongoDB
- **Scraping**: Playwright for JavaScript-heavy sites, aiohttp/BeautifulSoup for static
- **Push Notifications**: Expo Push Service with backend integration

## What's Been Implemented

### February 23, 2026 - Current Session

#### Completed
1. **PushNotificationSettings Import Fix**
   - Fixed incorrect import path in `PushNotificationSettings.tsx` (was `../../utils/colors`, changed to `../utils/colors`)
   - Component now renders correctly in Profile page

2. **Chat Function Reference Fix** (via Testing Agent)
   - Fixed `sendMessage` → `handleSendMessage` reference in tender detail chat section
   - Chat send button now works correctly

3. **Country Filter Fix (NEW)**
   - Fixed useEffect logic in index.tsx to properly trigger API calls when country filter changes
   - German flag (🇩🇪) now correctly filters to German tenders only
   - Swiss flag (🇨🇭) now correctly filters to Swiss tenders (40 found)
   - Filter can be toggled off by clicking the same flag again
   - Filter counts update dynamically based on selected country

4. **Verified All UI Features Working**
   - Login flow with valid credentials
   - Tenders list (1000 tenders displayed)
   - Tender detail page with Claim & Chat sections
   - Profile page with Push Notification Settings
   - Country filter tabs (Germany/Switzerland)
   - All navigation tabs functional

5. **Entwicklungsstadt.de News Scraper (NEW)**
   - Added new scraper for https://www.entwicklungsstadt.de/
   - Scrapes Berlin, Hamburg, Frankfurt, Potsdam construction news
   - 15+ articles per scrape with proper categorization (Wohnungsbau, Gewerbebau, Infrastruktur, etc.)
   - High relevance boost (+20) for construction-focused content

6. **simap.ch Swiss Tender Scraping (Previously FIXED)**
   - Updated scraper to use current simap.ch portal (not archive)
   - Successfully scraped 40 Swiss tenders from simap.ch
   - Proper 2026+ date filtering
   - Categories: Bauarbeiten, Hochbau, Tiefbau, Architektur

2. **Tender Claim & Chat UI**
   - Added "Claim Tender" button for team coordination
   - Added "Team Discussion" collapsible chat section
   - Chat with message history and real-time input
   - Shows who claimed each tender

3. **Real-Time Push Notifications (Backend Complete)**
   - Push token registration/unregistration endpoints
   - `send_push_notifications()` using Expo Push Service
   - Auto-notify users when new tenders scraped
   - Frontend NotificationContext and service implemented

4. **Backend Optimizations**
   - MongoDB connection pooling
   - Database indexes on filter fields
   - API pagination (default 1000, max 5000)
   - Caching for users/stats endpoints
   - Rate limiting

## Database Stats (Current)
- **Total Tenders**: 3718
  - Germany: 3639
  - Switzerland: 40
  - International: 39
- **Users**: 10
- **Developer Projects**: 19

## Test Credentials
| Email | Password | Role | Can Share |
|-------|----------|------|-----------|
| director@grovellows.de | Director123 | Director | Yes |
| stephan.hintzen@grovellows.de | Stephan123 | Partner | Yes |
| jurgen.volm@grovellows.de | Jurgen123 | Partner | Yes |
| parth.sheth@grovellows.de | Parth123 | Project Manager | Yes |
| phillip.kanthack@grovellows.de | Phillip123 | Project Manager | Yes |
| vesna.udovcic@grovellows.de | Vesna123 | Admin | No |

## Push Notification API Endpoints
- `POST /api/push-tokens` - Register push token
- `DELETE /api/push-tokens/{user_id}` - Unregister tokens
- `GET /api/push-tokens/status` - Get notification status
- `POST /api/notifications/send` - Send notifications (admin)
- `POST /api/notifications/test` - Test notification

## Key Files
- `/app/backend/server.py` - Main API with push notifications
- `/app/backend/comprehensive_scraper.py` - TED + simap.ch scraper
- `/app/frontend/app/tender/[id].tsx` - Tender detail with Claim & Chat
- `/app/frontend/services/notifications.ts` - Push notification service
- `/app/frontend/contexts/NotificationContext.tsx` - Notification state

## Remaining Tasks

### Completed
- [x] Notification settings UI in profile page
- [x] Market News real scraper (300+ articles from 7 sources)
- [x] Load testing for backend optimizations
- [x] News & Developer Projects sharing functionality
- [x] ESLint TypeScript configuration fixed
- [x] EAS development build configuration

### P2 - Medium Priority
- [ ] Build and distribute development APK for native testing

### P3 - Low Priority
- [ ] Push notification testing on physical device

## Scraper Sources
- **Germany**: Ausschreibungen Deutschland, Vergabe Bayern, TED Europa
- **Switzerland**: simap.ch (working!)
- **International**: TED Europa (multiple EU countries)
