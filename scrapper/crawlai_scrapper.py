import re
import json
from anthropic import AsyncAnthropic
from crawl4ai import AsyncWebCrawler, CacheMode

from config import Settings

settings = Settings()


class scrapper:
    @staticmethod
    async def crawl_dynamic_content(url: str):
        async with AsyncWebCrawler(verbose=False) as crawler:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }

                result = await crawler.arun(
                    url=url,
                    # Content filtering
                    word_count_threshold=10,
                    excluded_tags=[],
                    exclude_external_links=False,
                    # Content processing
                    process_iframes=False,
                    remove_overlay_elements=False,
                    extract_images=False,  # Disable image extraction
                    # Cache control
                    cache_mode=CacheMode.ENABLED,  # CacheMode.DISABLED,
                    magic=True,
                    wait_for_selector="body",
                    page_timeout=20000,
                    headers=headers,
                )

                if result.success and result.markdown:
                    return {
                        "url": result.url,
                        "content": result.markdown,
                        "internal_links": result.links.get("internal", []),
                        "external_links": result.links.get("external", []),
                    }
                else:
                    print(f"No content extracted from {url}")
                    return {"error": "No content extracted", "url": url}

            except Exception as e:
                print(f"Error crawling {url}: {str(e)}")
                return {"error": str(e), "url": url}

    @staticmethod
    async def get_final_structured_data_from_content_claude(
        content: str, location: str, postcode: str
    ):
        # Initialize Anthropic client
        client = AsyncAnthropic(api_key=settings.ANTHROPIC)

        # IMPORTANT: ONLY extract business data if ALL these conditions are met:
        prompt = """
        The HTML content is extracted in markdown format.


        As an expert website data extraction system, analyze the following content and extract all business-related information. Focus on identifying and extracting:
            1. The business address MUST contain the exact postcode: {postcode} or nearby postcode only
            2. If these conditions are not met exactly, return an empty array []

        1. Business Names: Extract complete company/business names
        2. Email Addresses: Extract the complete email address of the business
        3. Address: Extract complete postal/location address Example: ( 87 Barcom Avenue, DARLINGHURST NSW 2010) , ( 123 Main Street, SYDNEY NSW 2000)
        4. Phone Numbers: Extract the complete phone number of the business (international format if present) Example: (02) 9391 1234, (02) 9391 1234
        5. Website Links: Extract Business website URL no slug  Example: https://www.example.com
        6. Postcode: Extract the postcode based on the address
        7. Internal Navigation Link: Extract the correct internal navigation link of the content within the website Example: https://www.example.com/about

        Return ONLY a JSON array containing objects with these exact fields, with no additional text or formatting:
        [
          {{
            "business_name": string,
            "address": string,
            "phone_number": string,
            "email": string,
            "website_link": string,
            "postcode": string,
            "internal_navigation_link": string
          }}
        ]

        Content to analyze:
        {content}

           Remember: Return an empty array [] if the postcode {postcode} and location {location} don't match exactly.
           Return ONLY the JSON array, nothing else.
        """

        try:
            response = await client.messages.create(
                model="claude-3-haiku-20240307",  # claude-3-haiku-20240307 - haiku 3 , claude-3-5-haiku-20241022 - haiku 3.5
                max_tokens=4000,
                temperature=0.7,
                system="You are a precise data extraction assistant. Always return valid JSON arrays.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt.format(
                            content=content, location=location, postcode=postcode
                        ),
                    }
                ],
            )

            # Extract JSON from Claude's response
            print(response)
            response_text = response.content[0].text

            return response_text

        except Exception as e:
            print(f"Error in data extraction: {str(e)}")
            return []

    @staticmethod
    async def get_null_data_from_content_claude(content: str, data: dict) -> dict:
        # Initialize Anthropic client
        client = AsyncAnthropic(api_key=settings.ANTHROPIC)

        prompt = """
        Analyze the following HTML content (in markdown format) and extract only missing information to fill null or empty fields in the provided business data. Only extract information that matches the exact business name and location.

        Current business data:
        {data}

        Rules for extraction:
        1. Only fill empty/null fields - do not override existing data
        2. Only extract information that clearly belongs to this specific business
        3. Validate all extracted information:
           - Phone: Must be Australian format (e.g., (02) 9391 1234, 0412 345 678)
           - Email: Must be a valid business email
           - Website: Must be complete URL without tracking parameters
           - Address: Must include street, suburb, state and postcode
           - Postcode: Must be 4 digits and match the address

        Content to analyze:
        {content}

        Return ONLY a JSON object with the same structure as the input data, containing only newly found information for empty fields. Example:
        {{
          "phone_number": "0291234567",  // only if current phone_number is empty
          "email": "contact@business.com",  // only if current email is empty
          "website_link": "https://www.example.com",  // only if current website_link is empty
          "postcode": "2021",  // only if current postcode is empty
          // ... other fields only if they're currently empty
        }}
        """

        response = await client.messages.create(
            model="claude-3-haiku-20240307",  # claude-3-haiku-20240307 - haiku 3 , claude-3-5-haiku-20241022 - haiku 3.5
            max_tokens=4000,
            temperature=0.7,
            system="You are a precise data extraction assistant. Always return valid JSON arrays.",
            messages=[
                {
                    "role": "user",
                    "content": prompt.format(content=content, data=data),
                }
            ],
        )

        # Extract JSON from Claude's response
        response_text = response.content[0].text
        try:
            # Remove any markdown code block syntax if present
            clean_response = response_text.strip("`").replace("json\n", "")
            return json.loads(clean_response)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return {}

    @staticmethod
    async def extract_contact_info(url: str) -> dict:
        async with AsyncWebCrawler(verbose=False) as crawler:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }

                result = await crawler.arun(
                    url=url,
                    # Content filtering - focus on main content areas
                    word_count_threshold=5,  # Lower threshold for contact pages
                    excluded_tags=["script", "style", "header", "nav", "footer"],
                    exclude_external_links=True,
                    # Content processing
                    process_iframes=False,
                    remove_overlay_elements=True,
                    extract_images=False,
                    # Cache control
                    cache_mode=CacheMode.ENABLED,
                    magic=True,
                    wait_for_selector="body",
                    timeout=30,  # Reduced timeout for contact pages
                    headers=headers,
                    respect_robots_txt=True,
                )

                if result.success and result.markdown:
                    # Regular expressions for contact information
                    phone_pattern = r"(?:(?:\+61|0)[23478])(?:[ -]?[0-9]){8}|(?:(?:\+61|0)[23478])(?:[ -]?[0-9]){8}|04[0-9]{2}(?:[ -]?[0-9]){6}"
                    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

                    content_text = result.markdown

                    # Extract phone numbers
                    phone_matches = re.findall(phone_pattern, content_text)
                    phone = (
                        phone_matches[0].replace(" ", "").replace("-", "")
                        if phone_matches
                        else ""
                    )

                    # Extract emails
                    email_matches = re.findall(email_pattern, content_text)
                    email = ""
                    if email_matches:
                        valid_emails = [
                            e
                            for e in email_matches
                            if not any(
                                exclude in e.lower()
                                for exclude in ["example.com", "domain.com"]
                            )
                        ]
                        if valid_emails:
                            email = valid_emails[0].lower()

                    return {
                        "success": True,
                        "phone_number": phone,
                        "email": email,
                        "url": result.url,
                    }
                else:
                    print(f"No content extracted from {url}")
                    return {
                        "success": False,
                        "error": "No content extracted",
                        "url": url,
                        "phone_number": "",
                        "email": "",
                    }

            except Exception as e:
                print(f"Error crawling {url}: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "url": url,
                    "phone_number": "",
                    "email": "",
                }
