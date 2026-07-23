from flask import Flask, send_from_directory, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
import ssl
import json
import sqlite3
import pg8000.dbapi
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables (local dev only; Vercel injects them natively)
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

app = Flask(__name__)
# Secret key for session cookie encryption
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or 'default_fallback_secret_key_129837128937'

# Force secure cookies in production (HTTPS)
IS_PRODUCTION = os.environ.get('VERCEL_ENV') in ('production', 'preview')
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Master Seed Data for DB Initialization
SEED_RESEARCH_DATA = {
    "brick": {
        "title": "Brick by Byte",
        "desc": "Intelligent smart city ecosystems that sense, connect, and respond to a rapidly changing world.",
        "meta": "Focus: Urban Infrastructure & IoT friction.",
        "stats": [85, 70, 90, 60, 75],
        "tax": [12, 18, 5, 22],
        "display_order": 1,
        "problems": [
            {
                "problem_key": "brick-0",
                "title": "Fragmented Urban Data Silos",
                "detail": "City authorities fail to anticipate disasters like floods and infrastructure failures because data from IoT, weather, and citizen reports remain isolated.",
                "context": "Legacy municipal software contracts intentionally silo data to force vendor lock-in. Emergency, sanitation, and transit departments use proprietary databases lacking unified APIs.",
                "impact": "Forces cities into reactive disaster management. For instance, flood warnings are delayed until physical infrastructure is breached, increasing economic damage and delaying emergency response by critical hours.",
                "tags": ["Data Governance", "Vendor Lock-in", "Reactive Mgmt"]
            },
            {
                "problem_key": "brick-1",
                "title": "Micro-climate Heat Alleyways",
                "detail": "Traditional city-wide sensors miss localized heat pockets in narrow alleyways, leading to inaccurate emergency medical responses during heatwaves.",
                "context": "Macro-level weather stations are placed in open areas (airports, parks). They fail to account for the 'canyon effect' of concrete and glass trapping heat in dense, low-income urban grids.",
                "impact": "Ambulance routing algorithms under-prioritize specific high-density neighborhoods during heatwaves, resulting in preventable hyperthermia fatalities among vulnerable populations.",
                "tags": ["Sensor Blindspots", "Urban Design", "Health Inequity"]
            },
            {
                "problem_key": "brick-2",
                "title": "Ghost Data Storage Costs",
                "detail": "Massive volumes of 'heartbeat' data from idle infrastructure sensors create an invisible carbon footprint through server cooling and storage costs.",
                "context": "Smart city grids are programmed to log state data ('I am functioning') every millisecond. 99% of this data is noise, yet it is transmitted and stored indefinitely on cloud servers.",
                "impact": "Municipalities bleed budget on AWS/Azure storage fees for useless data, while the energy required to cool these data centers negates the carbon savings the 'smart' grids were supposed to achieve.",
                "tags": ["Cloud Waste", "IoT Noise", "Carbon Footprint"]
            },
            {
                "problem_key": "brick-3",
                "title": "Sensor Decay Deserts",
                "detail": "Suburbs experiencing 'maintenance lag' where failed hardware creates blind spots in traffic management, disproportionately affecting outer-city commuters.",
                "context": "Grant money funds the installation of IoT infrastructure, but municipal budgets rarely allocate funds for the ongoing maintenance and calibration of delicate sensors exposed to weather.",
                "impact": "Algorithms rely on broken sensor data, causing automated traffic lights to stall grids, or worse, environmental monitors failing to report toxic runoff in neglected districts.",
                "tags": ["Maintenance Deficit", "Infrastructure Decay", "Civic Budgets"]
            },
            {
                "problem_key": "brick-4",
                "title": "Algorithmic Redlining in Smart Policing",
                "detail": "Predictive policing algorithms trained on historical arrest data endlessly direct patrols to minority neighborhoods, creating a self-fulfilling feedback loop of surveillance.",
                "context": "Machine learning models are fed decades of biased arrest records rather than actual crime rates. The models conflate 'heavily policed areas' with 'high crime areas'.",
                "impact": "Systemic erosion of trust in civic institutions. Resources are pulled away from investigating complex crimes in favor of over-policing minor infractions in targeted zip codes.",
                "tags": ["Algorithmic Bias", "Surveillance", "Civil Rights"]
            },
            {
                "problem_key": "brick-5",
                "title": "Digital Twin Desync",
                "detail": "A city's 'digital twin' simulation becomes dangerously inaccurate when physical utility repairs are done manually on the fly and not logged into the central database.",
                "context": "Field workers face emergencies (e.g., burst pipes) and perform ad-hoc fixes that differ from the official blueprint. The UI for updating the digital twin is often too complex for field use.",
                "impact": "When automated systems or future contractors rely on the 'desynced' digital twin, they accidentally sever power lines or drill into active water mains, causing cascading utility failures.",
                "tags": ["Data Desync", "Human-in-the-loop", "Utility Risk"]
            },
            {
                "problem_key": "brick-6",
                "title": "Cross-Sector Policy Blindspots (The Disconnected Urban Genome)",
                "detail": "Decision-makers manage cities using isolated metrics (e.g., traffic vs. water vs. crime), failing to understand how interventions in one sector cascade into unintended consequences across the entire urban ecosystem.",
                "context": "Urban data is inherently siloed by departmental jurisdiction. Planners lack a unified predictive model—a 'City DNA'—that correlates multiple datasets to reveal the interactions and long-term effects of complex policies.",
                "impact": "Cities waste billions on isolated fixes that treat symptoms rather than systemic root causes. A mobility intervention might inadvertently degrade environmental health or water security, accelerating urban decay due to a lack of holistic multi-variable simulation.",
                "tags": ["Systems Thinking", "Policy Myopia", "Urban Planning"]
            }
        ]
    },
    "popcorn": {
        "title": "Reclaiming Popcorn Brains",
        "desc": "Technologies that empower individuals to break unhealthy digital cycles and reclaim time.",
        "meta": "Focus: Attention Economy & Cognitive Health.",
        "stats": [95, 80, 75, 85, 90],
        "tax": [5, 25, 30, 10],
        "display_order": 2,
        "problems": [
            {
                "problem_key": "popcorn-0",
                "title": "Context Switching Lag",
                "detail": "The 23-minute average recovery time lost after a 'quick' notification check, specifically impacting deep-work professions like research and coding.",
                "context": "The human brain must flush working memory to process a new stimulus (an email ping), and then painstakingly rebuild that context to return to the original complex task.",
                "impact": "A structural collapse in global productivity and innovation. Knowledge workers spend up to 40% of their day purely recovering from micro-interruptions rather than producing value.",
                "tags": ["Productivity Drain", "Neurology", "Deep Work"]
            },
            {
                "problem_key": "popcorn-1",
                "title": "Algorithmic Mirroring",
                "detail": "The gradual loss of linguistic variety as predictive text and LLMs narrow the user's own vocabulary through constant suggestions.",
                "context": "Autocorrect and generative AI prioritize the most statistically common phrasing. As users accept these suggestions for efficiency, their unique voice and edge-case vocabulary atrophy.",
                "impact": "A homogenization of human thought and culture. We are entering an era of 'average communication', reducing our cognitive ability to articulate complex, nuanced, or highly emotional states.",
                "tags": ["Linguistic Decay", "AI Homogenization", "Cognitive Atrophy"]
            },
            {
                "problem_key": "popcorn-2",
                "title": "Phantom Vibration Habituation",
                "detail": "The neurological scarring where individuals feel phone notifications even without a device present, causing constant cortisol spikes.",
                "context": "Years of variable reward conditioning (similar to slot machines) have hyper-sensitized the somatosensory cortex to anticipate the specific vibration frequency of mobile devices.",
                "impact": "Chronic elevation of base stress levels. This leads to adrenal fatigue, disrupted sleep architectures, and a baseline state of hyper-vigilance that damages long-term heart health.",
                "tags": ["Conditioning", "Cortisol", "Sensory Illusion"]
            },
            {
                "problem_key": "popcorn-3",
                "title": "Infinite Scroll Amnesia",
                "detail": "The phenomenon where users cannot recall a single piece of content they consumed just 5 minutes ago due to rapid dopamine dripping.",
                "context": "Short-form video platforms bypass the hippocampus (memory consolidation) by providing novel stimuli every 3 seconds, keeping the brain in a perpetual state of immediate reaction.",
                "impact": "Severe degradation of declarative memory capabilities in young adults. It erodes the ability to synthesize information into long-term worldviews, replacing knowledge with fleeting algorithmic moods.",
                "tags": ["Memory Loss", "Dopamine Drip", "Short-form Content"]
            },
            {
                "problem_key": "popcorn-4",
                "title": "Digital Hoarding Anxiety",
                "detail": "The subtle but chronic stress of accumulating thousands of unread emails, open browser tabs, and screenshot folders that users feel compelled to keep.",
                "context": "Storage has become cheap, eliminating the natural friction of 'cleaning up'. However, the psychological weight of an unorganized, infinite digital backlog remains a heavy cognitive load.",
                "impact": "Creates a paralyzing 'Zeigarnik effect'—the brain remembering uncompleted tasks. This manifests as chronic, low-level anxiety and avoidance behaviors regarding digital workspaces.",
                "tags": ["Digital Clutter", "Cognitive Load", "Anxiety"]
            },
            {
                "problem_key": "popcorn-5",
                "title": "Algorithmic Determinism",
                "detail": "The psychological claustrophobia of losing serendipity; the creeping realization that one's tastes and discoveries are entirely predictable.",
                "context": "Recommendation engines optimize for 'engagement' by feeding users only what they already like, trapping them in narrowing psychographic echo chambers.",
                "impact": "Destroys intellectual exploration and serendipitous discovery. It leads to extreme cultural polarization and a sense of existential dread that one is merely a predictable data point.",
                "tags": ["Echo Chambers", "Determinism", "Loss of Serendipity"]
            }
        ]
    },
    "hunger": {
        "title": "Safe Sources & Zero Hunger",
        "desc": "Solutions that rethink how we grow, manage, and sustain food resources.",
        "meta": "Focus: Food Security & Supply Chain Logistics.",
        "stats": [70, 95, 85, 75, 65],
        "tax": [20, 15, 10, 25],
        "display_order": 3,
        "problems": [
            {
                "problem_key": "hunger-0",
                "title": "Micronutrient Soil Depletion",
                "detail": "Modern yield-focused farming creates vegetables that look healthy but lack essential selenium and zinc, leading to 'hidden hunger' in wealthy nations.",
                "context": "Industrial agriculture incentivizes crop volume and visual perfection. Decades of aggressive monocropping and synthetic NPK fertilizers have stripped the soil of trace minerals.",
                "impact": "Populations consuming massive caloric surpluses are simultaneously suffering from severe clinical malnutrition, leading to immune deficiencies and developmental delays in children globally.",
                "tags": ["Hidden Hunger", "Soil Health", "Agri-economics"]
            },
            {
                "problem_key": "hunger-1",
                "title": "Cold Chain Breakdown Latency",
                "detail": "Minor power fluctuations in rural storage units that don't trigger alarms but accelerate spoilage of perishable vaccines and produce.",
                "context": "Current temperature sensors report absolute failures (power loss) but fail to register prolonged, subtle temperature drifts caused by aging compressors or micro-brownouts.",
                "impact": "Up to 30% of global perishable food is lost in transit. In healthcare, degraded vaccines are administered to populations under the false assumption they are still viable.",
                "tags": ["Logistics", "Food Waste", "Sensor Accuracy"]
            },
            {
                "problem_key": "hunger-2",
                "title": "Industrial Pre-Retail Waste",
                "detail": "The massive volume of edible food discarded during the processing phase (e.g., imperfectly sliced carrots) that never reaches a store shelf.",
                "context": "Retailers enforce draconian 'cosmetic standards' on suppliers. Automated sorting machines aggressively reject produce that is misshapen or slightly off-color, despite being perfectly nutritious.",
                "impact": "Millions of tons of edible food rot in processing facility landfills, generating massive methane emissions, while local food banks struggle with supply shortages.",
                "tags": ["Cosmetic Standards", "Supply Chain", "Methane"]
            },
            {
                "problem_key": "hunger-3",
                "title": "Aquifer Depletion Invisibility",
                "detail": "Large-scale agribusinesses unknowingly draining underground fossil water reserves much faster than they can naturally recharge.",
                "context": "Groundwater extraction is largely unmetered and invisible. Without real-time subterranean telemetry, farms pump water based on immediate surface crop needs, ignoring geological limits.",
                "impact": "Permanent collapse of land (subsidence) and the imminent exhaustion of aquifers that took millennia to fill, threatening multi-generational water security for entire continents.",
                "tags": ["Water Security", "Resource Exhaustion", "Telemetry"]
            },
            {
                "problem_key": "hunger-4",
                "title": "Monoculture Disease Susceptibility",
                "detail": "Extreme genetic uniformity in staple crops making entire regional food supplies devastatingly vulnerable to a single novel pathogen.",
                "context": "Corporate seed monopolies push highly optimized, genetically identical seeds for maximum yield. This eliminates the genetic firewall provided by biodiversity.",
                "impact": "A single fungal mutation (like Panama Disease in bananas) can wipe out an entire global harvest in one season, leading to sudden, catastrophic global food shortages.",
                "tags": ["Biodiversity", "Food Security", "Pathogens"]
            },
            {
                "problem_key": "hunger-5",
                "title": "Vertical Farming Energy Paradox",
                "detail": "High-tech indoor farms claiming sustainability while actually relying on massive amounts of fossil-fuel generated electricity.",
                "context": "Replacing the sun with LEDs and natural weather with HVAC systems requires astronomical baseline energy loads. The grid supplying this energy is still overwhelmingly fossil-based.",
                "impact": "These 'green' solutions currently emit more carbon per calorie produced than traditional farming, creating a facade of sustainability while exacerbating climate change.",
                "tags": ["Greenwashing", "Energy Intensity", "Agri-Tech"]
            }
        ]
    },
    "care": {
        "title": "Care Beyond Labels",
        "desc": "Innovations that address often-overlooked dimensions of health and well-being.",
        "meta": "Focus: Invisible Health & Social Isolation.",
        "stats": [60, 85, 95, 70, 80],
        "tax": [15, 10, 40, 5],
        "display_order": 4,
        "problems": [
            {
                "problem_key": "care-0",
                "title": "Diagnostic Delay for Rare Diseases",
                "detail": "The 'diagnostic odyssey' where patients spend 7+ years moving between specialists due to lack of cross-disciplinary data sharing.",
                "context": "Medical specialists operate in silos. A rheumatologist, a neurologist, and a dermatologist may all see the same patient over years but never aggregate their localized findings.",
                "impact": "Patients endure years of degenerative damage and psychological trauma from misdiagnoses. The healthcare system wastes millions on redundant tests and ineffective, generalized treatments.",
                "tags": ["Siloed Medicine", "Data Interoperability", "Rare Diseases"]
            },
            {
                "problem_key": "care-1",
                "title": "Chronic Pain Measurement Bias",
                "detail": "Subjective pain scales (1-10) that fail to account for cultural and neurodivergent differences in pain expression, leading to under-medication.",
                "context": "The universal 1-10 'smiley face' pain scale is deeply flawed. Neurodivergent individuals may mask pain heavily, while different cultures have varying stigmas around vocalizing agony.",
                "impact": "Systemic medical trauma. Vulnerable demographics are routinely dismissed as 'drug-seeking' or simply ignored, leaving them to suffer debilitating physical agony without intervention.",
                "tags": ["Medical Bias", "Pain Management", "Neurodiversity"]
            },
            {
                "problem_key": "care-2",
                "title": "Unpaid Caregiver Burnout",
                "detail": "The invisible economic and health collapse of family members providing 24/7 care without institutional support or monitoring.",
                "context": "Healthcare systems discharge chronically ill or aging patients to their families to cut hospital costs. The state provides zero training, mental health support, or financial compensation to these relatives.",
                "impact": "Caregivers suffer catastrophic financial ruin, severe depression, and physical collapse. This secondary health crisis forces both patient and caregiver back into the emergency system.",
                "tags": ["Shadow Economy", "Caregiving", "Systemic Failure"]
            },
            {
                "problem_key": "care-3",
                "title": "The 'Sandwich Generation' Squeeze",
                "detail": "Middle-aged adults facing simultaneous pressures of caring for aging parents and young children with zero systemic support.",
                "context": "Increased lifespans and delayed childbearing mean the timeline for eldercare and childcare now perfectly overlap during a worker's peak earning years.",
                "impact": "A massive exit of skilled (predominantly female) labor from the workforce, coupled with unprecedented rates of clinical anxiety and stress-induced autoimmune disorders.",
                "tags": ["Demographics", "Labor Force", "Mental Health"]
            },
            {
                "problem_key": "care-4",
                "title": "Stigma of Invisible Disabilities",
                "detail": "The severe lack of standard workplace accommodations for debilitating but invisible conditions like endometriosis or chronic fatigue syndrome.",
                "context": "Corporate HR policies require 'proof' of disability that often hinges on visible mobility aids. Conditions that fluctuate wildly day-to-day confuse rigid corporate accommodation frameworks.",
                "impact": "Highly capable individuals are managed out of their careers. They face quiet hostility from peers who perceive them as 'lazy', leading to severe financial instability and isolation.",
                "tags": ["HR Policies", "Invisible Illness", "Workplace Equity"]
            },
            {
                "problem_key": "care-5",
                "title": "Peri-Menopause Knowledge Gap",
                "detail": "The shocking lack of mandatory medical training and clinical research regarding the decade preceding menopause.",
                "context": "Historically, medical research centered entirely on male biology. Women's hormonal transitions were dismissed as 'hysteria' or simply ignored in clinical literature until very recently.",
                "impact": "Millions of women suffer severe cognitive fog, joint pain, and psychological distress without any medical support, often being misdiagnosed with early-onset dementia or clinical depression.",
                "tags": ["Medical Misogyny", "Research Gap", "Women's Health"]
            }
        ]
    },
    "industry": {
        "title": "Industry 4.0: Automation",
        "desc": "Smarter industrial ecosystems where productivity, sustainability, and safety go hand in hand.",
        "meta": "Focus: Smart Manufacturing & Workplace Dynamics.",
        "stats": [80, 65, 70, 90, 85],
        "tax": [35, 5, 15, 20],
        "display_order": 5,
        "problems": [
            {
                "problem_key": "industry-0",
                "title": "Legacy Machine Skill Gap",
                "detail": "Factories where high-tech sensors are slapped onto 40-year-old machines that no living engineer knows how to repair without the sensor's aid.",
                "context": "Retiring master technicians are replaced by iPads and dashboards. The tribal knowledge of how a machine sounds or vibrates is lost, replaced entirely by binary sensor readouts.",
                "impact": "When the sensor network fails or gets hacked, the entire production line freezes. The workforce has been deskilled to the point where manual override and diagnostic repair is impossible.",
                "tags": ["Deskilling", "Tribal Knowledge", "Fragility"]
            },
            {
                "problem_key": "industry-1",
                "title": "Rapid Iteration E-Waste",
                "detail": "The short lifespan of industrial IoT modules which become obsolete faster than the machinery they monitor, creating specialized electronic waste.",
                "context": "While a steel lathe might last 50 years, the microchips monitoring it become unsupported by software updates within 5 years. Upgrading requires entirely new physical chipsets.",
                "impact": "Factories are generating massive new streams of toxic, heavy-metal e-waste simply to maintain basic network connectivity, contradicting the sustainability promises of Industry 4.0.",
                "tags": ["Planned Obsolescence", "E-Waste", "Lifecycle Mismatch"]
            },
            {
                "problem_key": "industry-2",
                "title": "The 'Ghost Work' Exploitation",
                "detail": "The hidden, vast army of grossly underpaid human workers who manually label and correct the data needed to make industrial AI seem autonomous.",
                "context": "AI cannot autonomously recognize corner cases on an assembly line. It relies on thousands of gig-workers in developing nations to draw bounding boxes around images to train the models.",
                "impact": "The illusion of automation masks a massive new digital sweatshop economy. It drives down global wages and creates a fragile AI infrastructure wholly dependent on cheap, precarious human labor.",
                "tags": ["Digital Sweatshops", "AI Illusion", "Labor Rights"]
            },
            {
                "problem_key": "industry-3",
                "title": "Just-in-Time Fragility",
                "detail": "Hyper-optimized global manufacturing supply chains that completely collapse across industries the moment a single node fails.",
                "context": "Decades of MBA-driven efficiency eliminated all warehouse buffering. Components arrive exactly when needed to save storage costs, leaving zero margin for error.",
                "impact": "A single event (a stuck ship, a local lockdown, a storm) triggers a global cascade. Factories worldwide shut down within days, halting the production of everything from cars to medical devices.",
                "tags": ["Hyper-optimization", "Supply Chain", "Systemic Risk"]
            },
            {
                "problem_key": "industry-4",
                "title": "Over-Automation Complexity Collapse",
                "detail": "Industrial systems engineered with so many interlocking automated safeguards that novel faults cannot be diagnosed by human operators.",
                "context": "Safety layers are stacked upon safety layers. When a multi-variable error occurs, the system throws an opaque 'General Failure' code, shutting down completely to avoid liability.",
                "impact": "Downtime skyrockets because human engineers must blindly guess which of the 50 subsystems triggered the abort. The complexity of the safety mechanism becomes the primary point of failure.",
                "tags": ["Complexity Theory", "Opaque Systems", "Downtime"]
            },
            {
                "problem_key": "industry-5",
                "title": "Sensory Deprivation in Control Rooms",
                "detail": "Operators isolated in highly sterile, soundproof automated control rooms slowly losing critical situational awareness of the factory floor.",
                "context": "Modern plant design removes humans from the noisy, dangerous floor, placing them in distant, quiet rooms staring at screens. They lose the ambient, physical feedback of the machines.",
                "impact": "Operators fail to notice the subtle rumble of a failing pump or the smell of overheating plastic—cues that screen-based sensors might miss—leading to catastrophic physical explosions or failures.",
                "tags": ["Ergonomics", "Situational Awareness", "HCI"]
            }
        ]
    },
    "inclusive": {
        "title": "Inclusive Innovation",
        "desc": "An inclusive future enabled by equal access, participation, and opportunity.",
        "meta": "Focus: Equity & Accessibility Design.",
        "stats": [75, 90, 80, 85, 70],
        "tax": [10, 20, 20, 30],
        "display_order": 6,
        "problems": [
            {
                "problem_key": "inclusive-0",
                "title": "Cashless Society Exclusion",
                "detail": "The systematic removal of the unbanked and elderly from daily commerce as urban centers transition to 100% digital payments.",
                "context": "Businesses refuse cash to save on handling times and theft risk. However, acquiring a digital wallet requires a fixed address, a smartphone, and reliable internet.",
                "impact": "Creates immediate, hard barriers to survival for homeless populations, undocumented immigrants, and the elderly. They are effectively exiled from purchasing food or using public transit.",
                "tags": ["Financial Exclusion", "Cashless", "Urban Poverty"]
            },
            {
                "problem_key": "inclusive-1",
                "title": "Biometric Failures for Darker Skin",
                "detail": "Pervasive issues where facial recognition access controls and optical heart rate sensors consistently fail to register people with higher melanin levels.",
                "context": "Tech hardware and AI models are overwhelmingly tested on lighter-skinned datasets. Infrared sensors for soap dispensers and green-light sensors for smartwatches literally do not reflect well off dark skin.",
                "impact": "Racial bias encoded into the physical environment. People of color are locked out of secure buildings, denied sanitary facilities, and provided dangerously inaccurate health telemetry by medical devices.",
                "tags": ["Algorithmic Racism", "Hardware Bias", "Biometrics"]
            },
            {
                "problem_key": "inclusive-2",
                "title": "Nomadic Financial Exclusion",
                "detail": "The inability for pastoralists or digital nomads to access credit due to lack of a permanent 'fixed' address for KYC requirements.",
                "context": "Global 'Know Your Customer' (KYC) banking laws are rooted in 19th-century concepts of land ownership. They cannot process individuals whose primary residence shifts seasonally.",
                "impact": "Millions of legitimate workers are forced into predatory, high-interest shadow banking systems. It prevents wealth generation for indigenous populations and modern gig-workers alike.",
                "tags": ["KYC Laws", "Shadow Banking", "Mobility"]
            },
            {
                "problem_key": "inclusive-3",
                "title": "Inaccessible Digital Infrastructure",
                "detail": "The vast majority of essential government and health portals being incompatible with screen readers or keyboard-only navigation.",
                "context": "Web development prioritizes aesthetic frameworks (like React/Vue) over semantic HTML. Accessibility is treated as an optional, post-launch compliance checklist rather than a foundational architecture.",
                "impact": "Disabled citizens are legally disenfranchised. They cannot file taxes, book vaccine appointments, or access social security without relying entirely on a sighted/able-bodied proxy.",
                "tags": ["A11y", "Digital Rights", "Semantic Web"]
            },
            {
                "problem_key": "inclusive-4",
                "title": "Design for the 'Average' User",
                "detail": "Physical ergonomics and UI paradigms that optimize entirely for a mythical 'average' body and mind, marginalizing outliers.",
                "context": "Industrial design relies on 'standardized anthropometric data' (usually based on mid-20th-century military men) to mass-produce interfaces cheaply.",
                "impact": "Everything from seatbelts to smartphone keyboards creates micro-frictions or outright physical danger for anyone too short, too tall, left-handed, or neurodivergent, embedding subtle hostility into everyday life.",
                "tags": ["Ergonomics", "Standardization", "Hostile Design"]
            },
            {
                "problem_key": "inclusive-5",
                "title": "Automated Hiring Filter Exclusion",
                "detail": "Applicant Tracking Systems (ATS) instantly rejecting candidates whose resumes feature non-traditional formatting, employment gaps, or non-ivy keywords.",
                "context": "HR departments rely entirely on crude keyword-matching algorithms to filter thousands of applications, avoiding the labor of actually reading human experience.",
                "impact": "A massive, artificial talent shortage. Brilliant candidates from diverse backgrounds, non-linear career paths, or self-taught backgrounds are permanently firewalled out of the modern economy.",
                "tags": ["ATS Bias", "HR Tech", "Gatekeeping"]
            }
        ]
    },
    "resilience": {
        "title": "Building with Resilience",
        "desc": "Solutions that help communities anticipate, withstand, and recover from calamities.",
        "meta": "Focus: Disaster Recovery & Community Strength.",
        "stats": [85, 75, 60, 95, 90],
        "tax": [25, 10, 5, 40],
        "display_order": 7,
        "problems": [
            {
                "problem_key": "resilience-0",
                "title": "Post-Disaster 'Invisible' Trauma",
                "detail": "The psychological collapse of communities 6-12 months after a disaster, long after emergency aid and media attention have vanished.",
                "context": "Disaster funding is heavily front-loaded for physical infrastructure (rebuilding roads, dropping food). Mental health intervention is treated as a luxury and defunded once the cameras leave.",
                "impact": "A secondary crisis of substance abuse, domestic violence, and suicide ravages the surviving community. The societal fabric collapses just as the physical buildings are restored.",
                "tags": ["Mental Health", "Aid Lifecycle", "Secondary Crisis"]
            },
            {
                "problem_key": "resilience-1",
                "title": "Supply Chain Hoarding Cascades",
                "detail": "Rapid panic buying triggered by unverified social media rumors that instantly drains retail stocks, fabricating actual resource shortages.",
                "context": "Algorithmic social platforms amplify panic and fear to drive engagement. A single viral post about a potential shortage creates a self-fulfilling stampede on the physical supply chain.",
                "impact": "Vulnerable populations (like the elderly or poor who cannot afford to buy in bulk) are instantly deprived of essential goods like baby formula or medicine, manufactured entirely by digital hysteria.",
                "tags": ["Social Contagion", "Supply Shock", "Misinformation"]
            },
            {
                "problem_key": "resilience-2",
                "title": "Climate Gentrification",
                "detail": "Wealthy coastal populations retreating to higher, safer ground, subsequently pricing out the lower-income communities already living there.",
                "context": "As sea levels rise and insurance companies alter risk models, previously undesirable inland or elevated urban areas suddenly become highly valuable 'safe zones' for developers.",
                "impact": "Legacy, low-income communities are economically evicted from their historical homes and forced out toward the high-risk flood plains or fire zones the wealthy just abandoned.",
                "tags": ["Gentrification", "Climate Migration", "Housing Equity"]
            },
            {
                "problem_key": "resilience-3",
                "title": "Insurance Retreat from High-Risk Zones",
                "detail": "Major insurance companies abruptly pulling coverage from entire states prone to wildfires and hurricanes, leaving homeowners financially ruined.",
                "context": "Actuarial models show that extreme weather events are no longer anomalies but baselines. The financial risk of insuring certain geographies (e.g., California, Florida) mathematically breaks the insurance business model.",
                "impact": "The complete collapse of local real estate markets. Mortgages default as homes become uninsurable, wiping out generational wealth for the middle class and creating vast, unlivable 'uninsured deserts'.",
                "tags": ["Actuarial Science", "Economic Collapse", "Climate Risk"]
            },
            {
                "problem_key": "resilience-4",
                "title": "Cascading Infrastructure Failure",
                "detail": "The domino effect where a severe storm knocks out a power substation, which stops water pumps, which overheats telecom servers.",
                "context": "Modern critical infrastructures are hyper-interdependent but managed by separate, uncoordinated private entities. There is no central 'circuit breaker' to decouple these systems during a shock.",
                "impact": "A localized weather event rapidly transforms into a regional dark age. Communications, sanitation, and energy fail simultaneously, rendering standard emergency response protocols utterly useless.",
                "tags": ["Systemic Risk", "Interdependency", "Infrastructure"]
            },
            {
                "problem_key": "resilience-5",
                "title": "Warning Fatigue and Apathy",
                "detail": "Populations subjected to too many minor alerts or false alarms developing severe psychological apathy, causing them to ignore life-threatening orders.",
                "context": "Over-cautious municipalities blanket broadcast mobile alerts for minor storms or distant threats to avoid liability. The alert tone loses its neurological salience.",
                "impact": "When a truly catastrophic event (like a fast-moving wildfire) occurs, evacuation compliance drops to near zero. Citizens assume it's 'just another test', resulting in massive, preventable loss of life.",
                "tags": ["Alert Fatigue", "Human Psychology", "Emergency Comms"]
            }
        ]
    }
}


class SQLiteCursorWrapper:
    def __init__(self, cur):
        self.cur = cur

    @property
    def description(self):
        return self.cur.description

    def execute(self, query, params=()):
        sqlite_query = query.replace("%s", "?")
        sqlite_query = sqlite_query.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
        self.cur.execute(sqlite_query, params)
        return self

    def fetchone(self):
        return self.cur.fetchone()

    def fetchall(self):
        return self.cur.fetchall()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cur.close()


class SQLiteConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return SQLiteCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_db_connection():
    database_url = os.environ.get('DATABASE_URL', '').strip()
    
    if not database_url:
        db_path = os.path.join(PARENT_DIR, 'local_dev.db')
        sqlite_conn = sqlite3.connect(db_path)
        return SQLiteConnectionWrapper(sqlite_conn)

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    result = urlparse(database_url)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port or 5432

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = pg8000.dbapi.connect(
        user=username,
        password=password,
        host=hostname,
        port=port,
        database=database,
        ssl_context=ssl_ctx
    )
    return conn


def fetchall_dict(cur):
    desc = cur.description
    if not desc:
        return []
    columns = [col[0] for col in desc]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def fetchone_dict(cur):
    desc = cur.description
    if not desc:
        return None
    columns = [col[0] for col in desc]
    row = cur.fetchone()
    if row:
        return dict(zip(columns, row))
    return None


def get_initials(name):
    words = name.strip().split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    elif len(words) == 1 and len(words[0]) >= 2:
        return (words[0][0] + words[0][1]).upper()
    elif len(words) == 1:
        return words[0][0].upper()
    return "??"


# Database Setup
def init_db():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    handle TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );
            """)

            # Votes table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    problem_key TEXT NOT NULL,
                    vote_value INTEGER NOT NULL,
                    PRIMARY KEY (user_id, problem_key)
                );
            """)

            # Tracks table (Dynamic Research Blueprints)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    key TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    desc_text TEXT,
                    meta_text TEXT,
                    stats TEXT,
                    tax TEXT,
                    display_order INTEGER DEFAULT 0
                );
            """)

            # Problems table (Dynamic Research Issues)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS problems (
                    id SERIAL PRIMARY KEY,
                    problem_key TEXT UNIQUE NOT NULL,
                    track_key TEXT REFERENCES tracks(key) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    detail TEXT,
                    context TEXT,
                    impact TEXT,
                    tags TEXT
                );
            """)

            # Seed default admin account if needed
            cur.execute("SELECT id, password FROM users WHERE LOWER(handle) = 'admin';")
            admin_user = fetchone_dict(cur)
            admin_pw = os.environ.get('ADMIN_PASSWORD') or 'admin123'
            hashed_pw = generate_password_hash(admin_pw)

            if not admin_user:
                cur.execute(
                    "INSERT INTO users (name, handle, password) VALUES (%s, %s, %s);",
                    ('Admin User', 'admin', hashed_pw)
                )
                print("Admin user seeded successfully.")
            elif not check_password_hash(admin_user['password'], admin_pw):
                cur.execute(
                    "UPDATE users SET password = %s WHERE LOWER(handle) = 'admin';",
                    (hashed_pw,)
                )
                print("Admin user password updated successfully.")

            # Seed tracks and problems if empty
            cur.execute("SELECT count(*) as cnt FROM tracks;")
            cnt_row = fetchone_dict(cur)
            if not cnt_row or cnt_row['cnt'] == 0:
                print("Seeding tracks and problems into database...")
                for track_key, track_data in SEED_RESEARCH_DATA.items():
                    cur.execute("""
                        INSERT INTO tracks (key, title, desc_text, meta_text, stats, tax, display_order)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(key) DO NOTHING;
                    """, (
                        track_key,
                        track_data['title'],
                        track_data['desc'],
                        track_data['meta'],
                        json.dumps(track_data['stats']),
                        json.dumps(track_data['tax']),
                        track_data.get('display_order', 0)
                    ))

                    for p in track_data['problems']:
                        cur.execute("""
                            INSERT INTO problems (problem_key, track_key, title, detail, context, impact, tags)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT(problem_key) DO NOTHING;
                        """, (
                            p['problem_key'],
                            track_key,
                            p['title'],
                            p['detail'],
                            p['context'],
                            p['impact'],
                            json.dumps(p['tags'])
                        ))
                print("Tracks and problems seeded successfully.")

            conn.commit()
            print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


# Initialize Database immediately
init_db()


def serve_html(filename):
    filepath = os.path.join(PARENT_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(PARENT_DIR, filename)
    return send_from_directory(BASE_DIR, filename)


# ─── HTML Page Routes ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    return serve_html('final.html')

@app.route('/legacy')
def legacy():
    return serve_html('problem_blueprint_2898.html')

@app.route('/interactive')
def interactive():
    return serve_html('problem_blueprint_2898_inter.html')

@app.route('/interactive_2')
@app.route('/interactive2')
@app.route('/inter_2')
def interactive_2():
    return serve_html('problem_blueprint_2898_inter_2.html')

@app.route('/admin')
def admin():
    return serve_html('admin.html')


# ─── API Routes ────────────────────────────────────────────────────────────────

@app.route('/api/init', methods=['GET'])
def api_init():
    user_data = None
    user_votes = {}
    aggregated_scores = {}
    research_tracks = {}

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Fetch current logged-in user if session exists
            if 'user_id' in session:
                cur.execute("SELECT id, name, handle FROM users WHERE id = %s;", (session['user_id'],))
                db_user = fetchone_dict(cur)
                if db_user:
                    user_data = {
                        "name": db_user['name'],
                        "handle": db_user['handle'],
                        "initials": get_initials(db_user['name'])
                    }

                    cur.execute("SELECT problem_key, vote_value FROM votes WHERE user_id = %s;", (db_user['id'],))
                    for v in fetchall_dict(cur):
                        user_votes[v['problem_key']] = v['vote_value']

            # 2. Fetch aggregated scores for all problems
            cur.execute("SELECT problem_key, SUM(vote_value) as score FROM votes GROUP BY problem_key;")
            for s in fetchall_dict(cur):
                aggregated_scores[s['problem_key']] = int(s['score'])

            # 3. Fetch all tracks and problems dynamically from DB
            cur.execute("SELECT key, title, desc_text, meta_text, stats, tax, display_order FROM tracks ORDER BY display_order ASC, title ASC;")
            db_tracks = fetchall_dict(cur)

            cur.execute("SELECT id, problem_key, track_key, title, detail, context, impact, tags FROM problems ORDER BY id ASC;")
            db_problems = fetchall_dict(cur)

            # Group problems by track
            problems_by_track = {}
            for p in db_problems:
                t_key = p['track_key']
                if t_key not in problems_by_track:
                    problems_by_track[t_key] = []
                
                tags_parsed = []
                if p['tags']:
                    try:
                        tags_parsed = json.loads(p['tags']) if isinstance(p['tags'], str) else p['tags']
                    except Exception:
                        tags_parsed = [p['tags']]

                problems_by_track[t_key].append({
                    "problem_key": p['problem_key'],
                    "title": p['title'],
                    "detail": p['detail'],
                    "context": p['context'],
                    "impact": p['impact'],
                    "tags": tags_parsed,
                    "score": aggregated_scores.get(p['problem_key'], 0)
                })

            for t in db_tracks:
                key = t['key']
                stats_parsed = [0, 0, 0, 0, 0]
                tax_parsed = [0, 0, 0, 0]
                try:
                    if t['stats']:
                        stats_parsed = json.loads(t['stats']) if isinstance(t['stats'], str) else t['stats']
                    if t['tax']:
                        tax_parsed = json.loads(t['tax']) if isinstance(t['tax'], str) else t['tax']
                except Exception:
                    pass

                research_tracks[key] = {
                    "title": t['title'],
                    "desc": t['desc_text'],
                    "meta": t['meta_text'],
                    "stats": stats_parsed,
                    "tax": tax_parsed,
                    "problems": problems_by_track.get(key, [])
                }

    except Exception as e:
        print(f"Error in api_init: {e}")
    finally:
        if conn:
            conn.close()

    return jsonify({
        "user": user_data,
        "votes": user_votes,
        "scores": aggregated_scores,
        "tracks": research_tracks
    })


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    handle = data.get('handle', '').strip().lower()
    password = data.get('password', '')

    if not handle or not password:
        return jsonify({"error": "Handle and password are required"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, handle, password FROM users WHERE LOWER(handle) = %s;", (handle,))
            db_user = fetchone_dict(cur)
            if db_user and check_password_hash(db_user['password'], password):
                session['user_id'] = db_user['id']
                return jsonify({
                    "success": True,
                    "user": {
                        "name": db_user['name'],
                        "handle": db_user['handle'],
                        "initials": get_initials(db_user['name'])
                    }
                })
    except Exception as e:
        print(f"Error in api_login: {e}")
        return jsonify({"error": "Server error during login"}), 500
    finally:
        if conn:
            conn.close()

    return jsonify({"error": "Invalid handle or password"}), 401


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    return jsonify({"success": True})


@app.route('/api/vote', methods=['POST'])
def api_vote():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    problem_key = data.get('problem_key')
    vote_value = data.get('vote_value')

    if not problem_key or vote_value not in [1, -1, 0]:
        return jsonify({"error": "Invalid vote data"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if vote_value == 0:
                cur.execute(
                    "DELETE FROM votes WHERE user_id = %s AND problem_key = %s;",
                    (session['user_id'], problem_key)
                )
            else:
                cur.execute("""
                    INSERT INTO votes (user_id, problem_key, vote_value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, problem_key)
                    DO UPDATE SET vote_value = EXCLUDED.vote_value;
                """, (session['user_id'], problem_key, vote_value))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        print(f"Error in api_vote: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/change_password', methods=['POST'])
def api_change_password():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({"error": "Both current and new passwords are required"}), 400

    if len(new_password) < 4:
        return jsonify({"error": "New password must be at least 4 characters long"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT password FROM users WHERE id = %s;", (session['user_id'],))
            db_user = fetchone_dict(cur)
            if not db_user or not check_password_hash(db_user['password'], old_password):
                return jsonify({"error": "Incorrect current password"}), 400

            new_hashed_pw = generate_password_hash(new_password)
            cur.execute("UPDATE users SET password = %s WHERE id = %s;", (new_hashed_pw, session['user_id']))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        print(f"Error in api_change_password: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/admin/users', methods=['GET'])
def api_admin_users():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT handle FROM users WHERE id = %s;", (session['user_id'],))
            current_user = fetchone_dict(cur)
            if not current_user or current_user['handle'] != 'admin':
                return jsonify({"error": "Forbidden"}), 403

            cur.execute("SELECT name, handle FROM users ORDER BY name ASC;")
            users_list = fetchall_dict(cur)

            formatted_users = [
                {
                    "name": u['name'],
                    "handle": u['handle'],
                    "initials": get_initials(u['name'])
                }
                for u in users_list
            ]

            return jsonify({"users": formatted_users})
    except Exception as e:
        print(f"Error in api_admin_users: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/admin/create_user', methods=['POST'])
def api_admin_create_user():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    handle = data.get('handle', '').strip().lower()
    password = data.get('password', '')

    if not name or not handle or not password:
        return jsonify({"error": "Name, handle, and password are required"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT handle FROM users WHERE id = %s;", (session['user_id'],))
            current_user = fetchone_dict(cur)
            if not current_user or current_user['handle'] != 'admin':
                return jsonify({"error": "Forbidden"}), 403

            cur.execute("SELECT id FROM users WHERE LOWER(handle) = %s;", (handle,))
            if cur.fetchone():
                return jsonify({"error": "User with this handle already exists"}), 400

            hashed_pw = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (name, handle, password) VALUES (%s, %s, %s);",
                (name, handle, hashed_pw)
            )
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        print(f"Error in api_admin_create_user: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/admin/reset_user_password', methods=['POST'])
def api_admin_reset_user_password():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    handle = data.get('handle', '').strip().lower()
    new_password = data.get('new_password', '')

    if not handle or not new_password:
        return jsonify({"error": "Handle and new password are required"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT handle FROM users WHERE id = %s;", (session['user_id'],))
            current_user = fetchone_dict(cur)
            if not current_user or current_user['handle'] != 'admin':
                return jsonify({"error": "Forbidden"}), 403

            cur.execute("SELECT id FROM users WHERE LOWER(handle) = %s;", (handle,))
            target_user = fetchone_dict(cur)
            if not target_user:
                return jsonify({"error": "User not found"}), 404

            new_hashed_pw = generate_password_hash(new_password)
            cur.execute("UPDATE users SET password = %s WHERE id = %s;", (new_hashed_pw, target_user['id']))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        print(f"Error in api_admin_reset_user_password: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
