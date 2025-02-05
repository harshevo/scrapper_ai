import json
import asyncio
from anthropic import Anthropic
import typing_extensions as typing

from config import Settings
from tavily import TavilyClient

settings = Settings()

query_gen_prompt = """Generate 2 precise and targeted search queries to find current, active kids activities and programs in {location} (postcode: {postcode}). 

        Each query should combine elements from:
        Activities: {keywords}
        Venues: {venue}

#         Follow these search optimization rules:
#         1. Structure: [Activity Type] + [Age Group] + [Location/Venue] + [Action Words]
#         2. Include specific qualifiers:
#         - Age ranges: "0-5 years", "toddlers 2-3", "preschoolers"
#         - Current terms: "2024", "now", "current", "upcoming"
#         - Booking terms: "enroll", "register", "book online"
#         - Schedule terms: "term dates", "timetable", "weekly classes"

#         3. Use search operators when relevant:
#         - Use quotes for exact phrases
#         - Include OR operators for alternatives
#         - Add site-specific searches for known domains

#         4. Local specificity:
#         - Include suburb name AND postcode
#         - Add nearby suburb names
#         - Use local landmark references
#         - Include council or district name

#         5. Prioritize queries that would lead to:
#         - Active booking pages
#         - Current program schedules
#         - Direct contact information
#         - Official venue/provider websites

#         Example queries:
#         - "swimming lessons" AND ("babies" OR "toddlers") site:aquatic-centre.com.au {location} {postcode} enroll
#         - "{location} community centre" "term 1 2024" (art OR craft) classes preschool booking
#         - "weekly music classes" 0-5 years {location} {postcode} schedule

        Format each query to maximize relevance for local activity discovery and current program availability.

        Generate 2 Queries Strictly
        """

query_gen_prompt2 = """Generate only 15 different search queries with each keyword from the list: {keywords} to find relevant websites, listings, and information about kids activities in {location} (postcode: {postcode}) in the search engine. 
    Each query should combine activities from this list: {keywords}
    with venues from this list: {venue}
    
    Follow these rules for effective search queries:
    - Use the search engine to find relevant websites, listings, and information about kids activities in {location} (postcode: {postcode})
    - Include specific Sydney locations or suburbs when relevant
    - Add search-relevant terms like "classes", "schedule", "booking", "programs"
    - Include age groups (toddler, preschool, kids) where appropriate
    - Make queries specific enough to find actual programs, not general information
    - Query should be for kids focused activities with age 1-8
    - Format: "primary activity/topic" + "location/venue" + "relevant qualifiers"
    
    Examples:
    - "toddler swimming lessons aquatic centre eastern suburbs sydney schedule NSW 2008"
    - "kids art classes community centres inner west sydney bookings NSW 2008"
    - "Book Babies sessions Library Griffith NSW 2839"
    - "Kids Dance Classes Community Centre near 2839"


    Generate only 15 Queries Strictly
    """


class OutputFormat(typing.TypedDict):
    query_number: int
    query: str


async def query_generation(location: str, postcode: str):
    client = Anthropic(api_key=str(settings.ANTHROPIC))

    keywords = [
        "Arts & Crafts",
        "Book Babies",
        "Dance Classes",
        "Events",
        "Gymnastics",
        "Learn Languages",
        "Mums n Bubs Fitness Classes",
        "Music Classes",
        "Playgroup",
        "Playroom",
        "Rhyme Time",
        "Sensory Classes",
        "Singing Lessons",
        "Swimming Lessons",
        "Toddler Time",
    ]
    venue = [
        "Aquatic Centre",
        "Library",
        "Museum",
        "Play Centre",
        "Playground",
        "Toy Library",
        "Other",
        "Community Centre",
    ]

    prompt = query_gen_prompt2.format(
        keywords=keywords, venue=venue, location=location, postcode=postcode
    )

    # Use Claude to generate content
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        temperature=0.7,
        system="You are a search query generator. Output only valid JSON arrays containing strings of queries. Return only the JSON array, nothing else.",
        messages=[{"role": "user", "content": prompt}],
    )

    return json.loads(message.content[0].text)


def process_query(query):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response = loop.run_until_complete(get_relevant_urls(query))
    loop.close()
    return [url.get("url") for url in response.get("results", [])]


async def get_relevant_urls(query: str):
    # Step 1. Instantiating your TavilyClient
    tavily_client = TavilyClient(api_key=settings.TAVILY)

    # Step 2. Executing a simple search query
    response = tavily_client.search(
        query=query,
        search_depth="basic",  # basic deduct 1 api credit, advanced deduct 2 API credits
        include_answer=False,
        include_images=False,
        include_image_descriptions=False,
        include_raw_content=False,
        max_results=2,
        include_domains=[],
        exclude_domains=[],  # exclude social media sites
    )

    # Step 3. That's it! You've done a Tavily Search!
    # print(response)
    return response
