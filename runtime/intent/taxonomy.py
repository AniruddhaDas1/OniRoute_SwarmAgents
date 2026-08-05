"""Taxonomy dictionary and regex pattern matchers for Intent Analysis Engine."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

SUPPORTED_PROJECT_TYPES: List[str] = [
    "Website",
    "Landing Page",
    "CRM",
    "ERP",
    "Dashboard",
    "Portfolio",
    "Blog",
    "E-commerce",
    "Marketplace",
    "Restaurant",
    "School",
    "Hospital",
    "Mobile App",
    "Desktop App",
    "CLI Tool",
    "API",
    "SDK",
    "AI Agent",
    "Automation",
    "Browser Extension",
    "Game",
    "Unknown",
]

# Map project categories to canonical application runtime types
APPLICATION_TYPE_MAP: Dict[str, str] = {
    "Website": "Web Application",
    "Landing Page": "Web Application",
    "CRM": "Web Application",
    "ERP": "Web Application",
    "Dashboard": "Web Application",
    "Portfolio": "Web Application",
    "Blog": "Web Application",
    "E-commerce": "Web Application",
    "Marketplace": "Web Application",
    "Restaurant": "Web Application",
    "School": "Web Application",
    "Hospital": "Web Application",
    "Mobile App": "Mobile Application",
    "Desktop App": "Desktop Application",
    "CLI Tool": "CLI Tool",
    "API": "API Service",
    "SDK": "Software Development Kit",
    "AI Agent": "AI Agent System",
    "Automation": "Automation Script",
    "Browser Extension": "Browser Extension",
    "Game": "Game Application",
    "Unknown": "Unknown Application",
}

PRIMARY_INTENT_PATTERNS: Dict[str, str] = {
    r"\b(build|create|develop|make|generate|construct|implement|design|write|setup|set up)\b": "build",
    r"\b(refactor|restructure|rewrite|clean up|cleanup|modernize|redesign)\b": "refactor",
    r"\b(fix|repair|debug|patch|resolve|troubleshoot)\b": "fix",
    r"\b(optimize|speed up|improve|benchmark|tune)\b": "optimize",
    r"\b(audit|review|inspect|analyze|check|evaluate)\b": "audit",
    r"\b(deploy|publish|release|host)\b": "deploy",
    r"\b(test|add tests|unit test|e2e test|integration test)\b": "test",
}

PROJECT_TYPE_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(landing page|landing-page|sales page|squeeze page)\b", "Landing Page"),
    (r"\b(e-commerce|ecommerce|online store|web shop|shop|storefront|shopping app|shopping)\b", "E-commerce"),
    (r"\b(marketplace|multi-vendor|multi vendor)\b", "Marketplace"),
    (r"\b(crm|customer relationship management)\b", "CRM"),
    (r"\b(erp|enterprise resource planning)\b", "ERP"),
    (r"\b(dashboard|admin panel|analytics board|control panel|admin dashboard)\b", "Dashboard"),
    (r"\b(portfolio|personal site|personal website|showcase site)\b", "Portfolio"),
    (r"\b(blog|cms|content management system)\b", "Blog"),
    (r"\b(restaurant|dining|food ordering|cafe|menu app)\b", "Restaurant"),
    (r"\b(school|lms|learning management system|education|university|course platform)\b", "School"),
    (r"\b(hospital|healthcare|clinic|patient portal|medical app|medical)\b", "Hospital"),
    (r"\b(mobile app|mobile application|ios app|android app|flutter app|react native app)\b", "Mobile App"),
    (r"\b(desktop app|desktop application|electron app|tauri app)\b", "Desktop App"),
    (r"\b(cli tool|cli app|command line tool|command-line|terminal app|cli)\b", "CLI Tool"),
    (r"\b(rest api|graphql api|backend api|web service|api service|microservice|api)\b", "API"),
    (r"\b(sdk|client library|software development kit)\b", "SDK"),
    (r"\b(ai agent|swarm agent|autonomous agent|agentic system|llm agent|ai assistant)\b", "AI Agent"),
    (r"\b(automation|bot|workflow automation|scraper|web scraper|crawler|script)\b", "Automation"),
    (r"\b(browser extension|chrome extension|firefox extension|edge extension|extension)\b", "Browser Extension"),
    (r"\b(game|indie game|browser game|2d game|3d game|unity game)\b", "Game"),
    (r"\b(website|web site|site|web page|web app|web application)\b", "Website"),
]

LANGUAGES_TAXONOMY: Dict[str, str] = {
    r"\b(python|py)\b": "Python",
    r"\b(typescript|ts)\b": "TypeScript",
    r"\b(javascript|js)\b": "JavaScript",
    r"\b(go|golang)\b": "Go",
    r"\b(rust)\b": "Rust",
    r"\b(java)\b": "Java",
    r"(?:^|\s|\b)\.net\b|\bdotnet\b|\basp\.net\b|\bc#\b|\bcsharp\b": ".NET",
    r"\b(dart)\b": "Dart",
    r"\b(php)\b": "PHP",
    r"\b(c\+\+|cpp)\b": "C++",
    r"\b(ruby)\b": "Ruby",
    r"\b(swift)\b": "Swift",
    r"\b(kotlin)\b": "Kotlin",
}

FRAMEWORKS_TAXONOMY: Dict[str, str] = {
    r"\b(next\.js|nextjs|next)\b": "Next.js",
    r"\b(react\.js|reactjs|react)\b": "React",
    r"\b(vue\.js|vuejs|vue|nuxt|nuxtjs)\b": "Vue",
    r"\b(angular\.js|angularjs|angular)\b": "Angular",
    r"\b(flutter)\b": "Flutter",
    r"\b(react native|react-native)\b": "React Native",
    r"\b(node\.js|nodejs|node|express|nestjs)\b": "Node.js",
    r"\b(fastapi)\b": "FastAPI",
    r"\b(django)\b": "Django",
    r"\b(laravel)\b": "Laravel",
    r"\b(spring boot|springboot|spring)\b": "Spring",
    r"(?:^|\s|\b)\.net\b|\bdotnet\b|\basp\.net\b": ".NET",
    r"\b(svelte|sveltekit)\b": "Svelte",
    r"\b(remix)\b": "Remix",
    r"\b(astro)\b": "Astro",
}

DATABASE_TAXONOMY: Dict[str, str] = {
    r"\b(supabase)\b": "Supabase",
    r"\b(appwrite)\b": "Appwrite",
    r"\b(firebase|firestore)\b": "Firebase",
    r"\b(postgresql|postgres|pg)\b": "PostgreSQL",
    r"\b(mysql)\b": "MySQL",
    r"\b(mongodb|mongo)\b": "MongoDB",
    r"\b(redis)\b": "Redis",
    r"\b(sqlite)\b": "SQLite",
    r"\b(dynamodb)\b": "DynamoDB",
}

CLOUD_TAXONOMY: Dict[str, str] = {
    r"\b(docker|dockerfile|container)\b": "Docker",
    r"\b(kubernetes|k8s)\b": "Kubernetes",
    r"\b(aws|amazon web services)\b": "AWS",
    r"\b(gcp|google cloud)\b": "GCP",
    r"\b(azure)\b": "Azure",
    r"\b(vercel)\b": "Vercel",
    r"\b(netlify)\b": "Netlify",
    r"\b(firebase)\b": "Firebase",
    r"\b(cloudflare)\b": "Cloudflare",
    r"\b(supabase)\b": "Supabase",
    r"\b(appwrite)\b": "Appwrite",
}

AUTHENTICATION_TAXONOMY: Dict[str, str] = {
    r"\b(supabase auth|supabase)\b": "Supabase Auth",
    r"\b(firebase auth|firebase)\b": "Firebase Auth",
    r"\b(auth0)\b": "Auth0",
    r"\b(clerk)\b": "Clerk",
    r"\b(nextauth|next-auth|auth\.js)\b": "NextAuth",
    r"\b(oauth|oauth2)\b": "OAuth",
    r"\b(jwt|json web token)\b": "JWT",
    r"\b(appwrite auth|appwrite)\b": "Appwrite Auth",
}

INTEGRATIONS_TAXONOMY: Dict[str, str] = {
    r"\b(stripe|payments?)\b": "Stripe",
    r"\b(openai|gpt-4|gpt-3\.5|gpt)\b": "OpenAI",
    r"\b(gemini)\b": "Gemini",
    r"\b(anthropic|claude)\b": "Anthropic",
    r"\b(twilio)\b": "Twilio",
    r"\b(sendgrid)\b": "SendGrid",
}

UI_FRAMEWORKS_TAXONOMY: Dict[str, str] = {
    r"\b(tailwind|tailwindcss|tailwind css)\b": "Tailwind",
    r"\b(shadcn|shadcn/ui|shadcn ui)\b": "Shadcn",
    r"\b(material ui|mui)\b": "Material UI",
    r"\b(bootstrap)\b": "Bootstrap",
    r"\b(chakra|chakra ui)\b": "Chakra",
}

FEATURE_PATTERNS: Dict[str, str] = {
    r"\b(luxury real estate|real estate|property|properties)\b": "luxury_real_estate",
    r"\b(hotel|booking|reservation)\b": "hotel_booking",
    r"\b(payment|checkout|stripe|billing|subscription)\b": "payment_processing",
    r"\b(auth|login|signup|authentication|user management)\b": "user_authentication",
    r"\b(chat|messaging|real-time|realtime|websocket|live updates)\b": "realtime_communication",
    r"\b(dark mode|theme toggle|theming)\b": "dark_mode",
    r"\b(multi-language|i18n|translation|multilingual)\b": "internationalization",
    r"\b(search|filter|filtering|indexing)\b": "search_and_filter",
    r"\b(analytics|metrics|tracking)\b": "analytics",
    r"\b(notifications|email|push notifications)\b": "notifications",
}

CONSTRAINT_PATTERNS: Dict[str, str] = {
    r"\b(responsive|mobile friendly|mobile-first)\b": "responsive_design",
    r"\b(fast|high performance|scalable|low latency)\b": "high_performance",
    r"\b(secure|security|gdpr|hipaa|encrypted)\b": "security_compliance",
    r"\b(local-first|offline|offline-first)\b": "local_first",
    r"\b(lightweight|minimal|minimalist)\b": "minimal_dependencies",
    r"\b(microservices|microservice)\b": "microservices",
    r"\b(serverless)\b": "serverless",
}

IMPLIED_STACK_RULES: Dict[str, Dict[str, Any]] = {
    "Next.js": {
        "frameworks": ["React"],
        "languages": ["TypeScript", "JavaScript"],
        "application_type": "Web Application",
    },
    "React Native": {
        "frameworks": ["React"],
        "languages": ["JavaScript", "TypeScript"],
        "project_category": "Mobile App",
        "application_type": "Mobile Application",
    },
    "Flutter": {
        "languages": ["Dart"],
        "project_category": "Mobile App",
        "application_type": "Mobile Application",
    },
    "FastAPI": {
        "languages": ["Python"],
    },
    "Django": {
        "languages": ["Python"],
    },
    "Laravel": {
        "languages": ["PHP"],
    },
    "Spring": {
        "languages": ["Java"],
    },
    "Supabase": {
        "database": ["PostgreSQL", "Supabase"],
        "cloud": ["Supabase"],
    },
    "Firebase": {
        "database": ["Firebase"],
        "cloud": ["Firebase"],
    },
}
