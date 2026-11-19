# Amna Ahmad — Professional Profile & Knowledge Base

## About Me

I'm Amna Ahmad, a software engineer based in Rawalpindi, Pakistan. I have a Bachelor of Engineering in Software Engineering from NUST and professional experience spanning enterprise software development, web applications, API integrations and automation.

After an extended family-related career break, I returned to software development through freelance work, specialising in Wix Velo development and custom integrations. I'm now expanding further into backend engineering and AI engineering, building practical applications involving Python, LLMs, retrieval-augmented generation (RAG), APIs and automation.

I enjoy solving practical problems, understanding how systems work behind the scenes and building solutions that connect different technologies.

## Professional Background

### Education

**B.E. Software Engineering — National University of Sciences and Technology (NUST)**  
2002–2006

### Mobilink — Software Design & Development Engineer
November 2006 – April 2010

Worked on internal software and database-related systems, including:

- SQL Server 2005 databases for cellular statistics.
- ETL processes and data handling.
- SQL Server Reporting Services (SSRS).
- SharePoint-based helpdesk solutions.

### Motorola — Project Administrator
May 2006 – November 2006

Worked on project administration and internal process automation, including an Access-based inventory and invoicing system with barcode validation.

### Career Break and Return to Software Development

I took an extended career break for family responsibilities. I later returned to software development through freelance and client work, rebuilding my practical development experience and expanding my technical skills.

My recent work has included Wix Velo applications, custom backend functionality, third-party API integrations, payment systems and automation.

I have completed over 1,000 hours on Upwork with a 100% Job Success Score.

## What I Do Now

I work as an independent software developer, with experience in:

- Custom Wix Velo and Wix Studio development.
- JavaScript-based frontend and backend functionality.
- Third-party API integrations.
- Payment integrations, including Stripe and Square.
- Business workflow automation.
- CRM and email integrations.
- Python automation and browser automation.
- AI-powered applications and RAG systems.

I am actively transitioning towards broader backend and AI engineering opportunities rather than limiting my professional identity to Wix development.

## AI and Technical Learning

I am developing practical experience in:

- Python application development.
- OpenAI APIs and LLM-based applications.
- Retrieval-Augmented Generation (RAG).
- Embeddings and vector databases.
- Keyword, vector and hybrid retrieval.
- Cross-encoder and LLM-based reranking.
- Retrieval evaluation using metrics such as hit rate and Mean Reciprocal Rank (MRR).
- AI agents and tool calling.
- Prompt design and response evaluation.
- n8n and workflow automation.

I prefer learning by building projects, testing alternatives and understanding the underlying implementation rather than relying only on high-level frameworks.

## Selected Projects

### 1. FoodSafety RAG — Ask My Docs

**Live application:** https://ai-portfolio-rpy2.onrender.com/  
**Project documentation:** https://ai-portfolio-2ij.pages.dev/projects/ask-my-docs/  
**GitHub:** https://github.com/amna-ahmad-ch/ai-portfolio

**Short description**

I built and deployed a RAG application that answers food-safety questions using a collection of 12 USDA food-safety documents. The project explores how document chunking and retrieval strategies affect the quality of information retrieved for an LLM.

**Technical implementation**

- Python-based document ingestion and retrieval pipeline.
- USDA document processing and passage generation.
- Chroma vector database.
- OpenAI embeddings in the deployed application.
- Keyword and hybrid retrieval.
- LLM-generated answers using Groq.
- Source attribution and answer verification.

**Retrieval experiments**

I compared four document preparation strategies:

- 500-character chunks.
- 1,000-character chunks.
- Section-based chunks.
- AI-written passages.

I evaluated BM25 keyword retrieval, vector retrieval, hybrid retrieval, cross-encoder reranking and experimental Groq-based reranking.

Using a curated set of 16 questions:

- AI-written passages with vector retrieval achieved 16/16 retrieval hits and an MRR of 0.886.
- Experimental Groq reranking improved MRR to 0.964 while retaining 16/16 hits.

These are results from a small, project-specific evaluation set, not a general benchmark.

**Live application versus experiments**

The live application uses 109 AI-written passages, OpenAI embeddings, keyword-based/hybrid retrieval, top-five passage selection and Groq for answer generation.

The Groq reranking experiment is not part of the deployed application.

I also explored strict source-sentence matching as a safety measure. It was too restrictive when equivalent information had minor formatting differences, so this highlighted the need for more robust answer-grounding and verification methods.

**What I learned**

- How document structure and chunking affect retrieval.
- How keyword and semantic retrieval complement each other.
- How to evaluate retrieval using hit rate and MRR.
- Why retrieval success does not automatically guarantee answer correctness.
- Why answer grounding and evaluation need to be considered separately.

### 2. ReviewPulse — Wix Review Automation App

**Repository:** `post-booking-review`

**Short description**

I contributed to ReviewPulse, a Wix app designed for businesses using Wix Bookings. It automatically schedules and sends branded review-request emails after appointments, classes or courses, helping businesses collect customer reviews without following up manually.

Merchants configure review links, email templates and sending schedules through a Wix dashboard. The app also supports subscription tiers with usage limits and feature restrictions.

**Technical implementation**

- TypeScript and React.
- Wix CLI and `@wix/astro`.
- Wix Design System and `@wix/dashboard`.
- Wix Bookings webhooks.
- Wix Data CMS collections.
- Wix App Instance and billing APIs.
- Resend for transactional email.
- Playwright is not part of this project; scheduled delivery uses a cron-based backend process.
- Optional Sentry monitoring on Cloudflare.

**Architecture**

The application listens to Wix Bookings events and creates scheduled review requests. Each request is stored with a `scheduledSendAt` value.

A cron endpoint, `POST /api/cron/send-all-due`, processes requests that are ready to send. Resend handles email delivery, and signed tracking endpoints record opens and clicks.

The merchant dashboard displays statistics and recent activity.

**Subscription and lifecycle management**

- Supports Basic, Starter and Growth subscription tiers.
- Retrieves current plan information from Wix billing APIs.
- Applies usage limits and feature gates.
- Handles installation, uninstallation and billing lifecycle webhooks.
- Provisions settings during installation and cleans up collections during uninstallation.
- Reconciles plan-related settings when subscriptions change.

**Security and operations**

- Backend operations use elevated Wix SDK calls where required.
- Middleware protects cron and public routes.
- Shared secrets protect scheduled processing.
- Tracking links are signed.
- Structured debug logging and optional Sentry monitoring support troubleshooting.

**Technical discussion areas**

This project demonstrates practical experience with event-driven integrations, background processing, subscription-aware functionality, third-party platform APIs, data modelling and production operations.

**Ownership note:** Describe this as a project I contributed to. Do not claim sole ownership of the entire application unless I explicitly clarify my individual responsibilities.

### 3. Share a Book — Community Book-Sharing Application

**Live application:** https://share-a-book-bf6bc.web.app/

**Short description**

Share a Book is a free Progressive Web App (PWA) I built to help Pakistani school parents give away or sell used textbooks within their school communities.

**Technology stack**

- React 18.
- React Router 6.
- Vite 5.
- Tailwind CSS 4.
- Firebase Authentication.
- Cloud Firestore.
- Firebase Storage.
- Firebase Hosting.
- `vite-plugin-pwa` and Workbox.

**Main features**

- Phone number authentication using Firebase OTP.
- Parent onboarding with name and school selection.
- Browse and filter textbook listings by grade, subject and availability.
- Post, edit and manage books offered for free or for sale.
- Upload and compress book photos.
- Contact book owners through WhatsApp using a prefilled message.
- Report listings and submit support requests.
- Admin functionality for managing listings, schools, users and reports.

**Architecture**

The application uses a client-side architecture. React communicates directly with Firebase; there is no custom API server.

Firebase Authentication manages user sessions, while Firestore and Storage Security Rules enforce access permissions and ownership checks.

React route guards provide navigation and user-experience controls, but they are not treated as security boundaries.

The Firestore data model includes users, listings, schools, blocked users, reports, support messages and billing/status configuration.

Listing queries use composite indexes. Filters are applied in the browser because the application initially serves a relatively small school community.

**Technical challenges**

- Handling HEIC images from iPhones.
- Compressing large mobile camera images without exhausting browser memory.
- Addressing differences between Android and iOS photo handling.
- Configuring Firebase phone authentication for Pakistani phone numbers.
- Working through reCAPTCHA, authorized domains, SMS region restrictions and Firebase billing requirements.
- Designing Firestore and Storage rules to enforce data ownership and permitted operations.

**Security considerations and limitations**

Some controls are not fully enforced by Firebase Security Rules. In particular, the 20-active-listing limit and the owner deletion workflow are primarily handled in client code.

A future improvement would be to move these operations into trusted Cloud Functions or adjust the relevant security rules.

The project has a `functions/` scaffold, but Cloud Functions are not currently used.

**What I learned**

- Building and deploying a complete Firebase-backed application without a custom API server.
- Designing Firestore collections, queries and composite indexes.
- Using Firebase Security Rules as an authorization layer.
- Handling mobile image uploads and browser memory limitations.
- Understanding the difference between client-side validation and server-side security enforcement.

### 4. ClickUp → TopTracker Invoicer

**Repository:** `clickup-toptracker-invoicer`

**Short description**

I built a personal automation tool that turns my ClickUp time tracking into a draft invoice in TopTracker.

Once a week, I run a Python command that fetches my tracked hours, adds them to TopTracker as manual time entries, and creates a draft invoice.

Previously, I copied the information manually using Google Sheets. The tool automates that repetitive process, but it never sends an invoice. I review and submit it myself.

**How it works**

1. Fetches ClickUp time entries for the current week, previous week or a custom date range.
2. Converts them into invoice line items containing project, task, description, hours, rate and amount.
3. Uses Playwright to log into TopTracker through a real browser.
4. Adds manual time entries.
5. Opens the invoice creation page, sets the billing period and saves a draft.
6. Stops without sending the invoice.

It also supports `--dry-run` to preview hours without changing TopTracker and `--invoice-only` when time entries have already been added.

**Technology stack**

- Python 3.10+.
- ClickUp REST API.
- `requests`.
- Playwright with asynchronous Chromium.
- `python-dotenv`.
- `argparse`.

**Architecture**

- `clickup_client.py`: Fetches ClickUp time entries and converts them into invoice line items.
- `toptracker_bot.py`: Automates TopTracker login, manual time entries, date selection and draft invoice creation.
- `main.py`: Coordinates date ranges, dry runs, user confirmation and the overall workflow.

**Technical challenges**

- Handling a React date picker that ignored Playwright's `fill()` method.
- Setting dates using the expected format and triggering input, change and blur events.
- Avoiding premature form submission when interacting with date fields.
- Preventing overlapping time entries by assigning sequential time slots to tasks on the same day.
- Flattening multiline ClickUp descriptions and removing emoji for TopTracker's single-line field.
- Avoiding fragile sidebar text navigation by using direct application URLs.

**Safety and operations**

- Credentials and configuration are stored in a gitignored `.env.local` file.
- Invoices are drafts only; the script never sends them.
- `--headless` supports background runs.
- Headed mode is useful for debugging.
- Error screenshots are excluded from Git.

**Why Playwright instead of Zapier?**

TopTracker does not expose the APIs needed for this workflow. I used Playwright to automate the actual browser interface rather than relying on an integration platform that would need APIs that are unavailable.

The automation still includes a human review step before an invoice is submitted.

### 5. qflorist — Wix Stripe Checkout Integration

**Website:** https://www.qflorist.com/

I worked on a custom Stripe Checkout integration for a Wix website.

The integration uses Wix Velo backend functionality to create Stripe Checkout sessions and a custom frontend element to support the checkout experience.

This project involved connecting a website platform with an external payment provider and handling backend/frontend communication.

### 6. Virtual Adviser — AI-Powered Education Application

**Website:** https://www.cw-education.com/cw-virtual-adviser

I worked on a virtual adviser application involving OpenAI Assistant functionality.

The project explored integrating an AI assistant into an education-focused website to provide an interactive advisory experience.

### 7. Other Development Work

I have also worked on custom business applications, Wix Studio websites, CRM integrations, payment workflows, backend functionality and automation.

Relevant technologies and services have included:

- Pipedrive.
- Stripe and Square.
- Billit and Moneybird.
- Google Apps Script.
- n8n.
- PHP and Hostinger.
- Wix Velo and Wix Studio APIs.

## Technical Skills

### Programming Languages
- JavaScript.
- TypeScript.
- Python.
- SQL.
- PHP.

### Backend and APIs
- Node.js fundamentals.
- REST APIs.
- Webhooks.
- Authentication and authorization.
- Third-party API integrations.
- Backend business logic.

### Frontend
- React.
- Wix Studio.
- Wix Velo.
- HTML and CSS.
- Tailwind CSS.

### AI and Data
- OpenAI APIs.
- LLM applications.
- RAG.
- Embeddings.
- Chroma.
- BM25.
- Hybrid retrieval.
- Cross-encoder reranking.
- Retrieval evaluation.
- AI agents and tool calling.

### Databases and Cloud
- SQL Server.
- Firebase Authentication.
- Firestore.
- Firebase Storage.
- Chroma vector database.
- Supabase fundamentals.

### Automation and Integrations
- Playwright.
- n8n.
- Google Apps Script.
- Stripe.
- Square.
- Resend.
- CRM and payment integrations.

### Development Tools
- Git and GitHub.
- Cursor.
- VS Code.
- uv and Python virtual environments.
- Wix CLI.
- Vercel.
- Cloudflare.
- Firebase Hosting.

## Professional Interests and Goals

I am interested in remote software engineering opportunities, particularly:

- Backend engineering.
- Python and JavaScript/Node.js development.
- AI engineering.
- RAG and LLM applications.
- AI agents and workflow automation.
- API integrations and platform engineering.

I am open to remote roles, contract work and opportunities that allow me to grow into a broader software or AI engineering role.

I value practical engineering, clear communication, maintainable code and solving real business problems.

## Working Style

- I prefer understanding the underlying technical concepts rather than blindly copying solutions.
- I enjoy debugging and investigating why something fails.
- I like building practical applications that solve real problems.
- I value clear requirements and straightforward communication.
- I prefer honest descriptions of experience and do not want to exaggerate my expertise.
- I am comfortable learning unfamiliar tools and technologies when a project requires them.

## Links and Contact

- **AI portfolio:** https://ai-portfolio-2ij.pages.dev/
- **FoodSafety RAG documentation:** https://ai-portfolio-2ij.pages.dev/projects/ask-my-docs/
- **FoodSafety RAG live demo:** https://ai-portfolio-rpy2.onrender.com/
- **FoodSafety RAG GitHub:** https://github.com/amna-ahmad-ch/ai-portfolio
- **Wix portfolio:** https://wixstudio-1693278832.wixsite.com/amna-ahmad
- **LinkedIn:** https://www.linkedin.com/in/amna-ahmad-88abbb9b/
- **GitHub:** https://github.com/amna-ahmad-ch
- **Share a Book:** https://share-a-book-bf6bc.web.app/
- **qflorist:** https://www.qflorist.com/
- **Virtual Adviser:** https://www.cw-education.com/cw-virtual-adviser
- **Email:** amna.ahmad.ch@gmail.com
- **Location:** Rawalpindi, Pakistan

## Guidance for the Digital Twin

When answering questions about Amna:

1. Be accurate and distinguish between professional employment, freelance work, collaborative contributions and personal projects.
2. Describe ReviewPulse as a project she contributed to, not necessarily one she built entirely alone.
3. Describe Share a Book and ClickUp → TopTracker Invoicer as projects she built.
4. Do not claim that the experimental Groq reranking system is part of the deployed FoodSafety RAG application.
5. Do not present the FoodSafety RAG evaluation results as a large-scale benchmark.
6. Do not claim that ClickUp → TopTracker Invoicer sends invoices. It creates drafts only.
7. Do not claim Share a Book uses Cloud Functions as its active backend. It is a client-side React application using Firebase directly.
8. Do not describe Amna as having many years of professional AI engineering experience. Her AI engineering work is a developing area supported by practical projects and ongoing learning.
9. Present the career break honestly and positively, without making it the central theme of her professional identity.
10. Keep answers natural, concise and conversational. Expand technical details when the question calls for them.
11. Do not invent project metrics, client names, responsibilities, employment dates or technical capabilities.