import os
import json
import uvicorn
from pydantic import BaseModel
from time import perf_counter, sleep
from fastapi import FastAPI, HTTPException

from firebase import db
from config import Settings
from logger_config import get_logger
from crawler.tavily import process_query
from crawler.tavily import query_generation
from scrapper.crawlai_scrapper import scrapper
from concurrent_processing import concurrent_result

settings = Settings()

logger = get_logger("prospects")


app = FastAPI()


class LocationRequest(BaseModel):
    location: str
    postcode: str


# Take the address and postcode from the user
# Validate the address and postcode
# Generate the queries
# Fetch the exclusion list from the db and send to the tavily or think the other way for doing exclusion list
# loop the queries and send each query to the tavily api
# Get the relevant urls
# Loop through the urls and crawl the dynamic content
# Crawl scrape the content if the data is relevant and related ( may be apply some agentic behaviour)
# Extract Based on postcode and location
# Get the final structured data
# Return the final structured data
# store the final

process = concurrent_result(12)


@app.post("/process-location")
async def process_location(request: LocationRequest):
    try:
        ex_start = perf_counter()

        # step 1 : Take input from user
        location = request.location
        postcode = request.postcode

        # step 2 : Generate queries
        queries = await query_generation(location=location, postcode=postcode)
        print("-------------> generated queries", queries)
        logger.info(f"Generated queries: {queries}")

        # step 3 : Get relevant urls from tavily
        urls = []

        process.get_urls(process_query, queries, urls)  # multiprocessing
        print(f"URL ======>>>>> {urls}")
        logger.info(f"URL ======>>>>> {urls}")

        content_list = []

        # step 4 : Scrape data from all urls and store it in a list
        for url in urls:
            markdown_content = await scrapper.crawl_dynamic_content(url)
            if not markdown_content.get("error"):
                content_list.append(markdown_content)
            # else:
            #     print(f"Error crawling {url}: {markdown_content.get('error')}")
            #     continue

        print("-------------> content_list", len(content_list))
        logger.info(f"Content list length: {len(content_list)}")

        structured_data = []
        for content in content_list:
            data = await scrapper.get_final_structured_data_from_content_claude(
                content.get("content"), location, postcode
            )
            print(f" structured data --> {data}")
            logger.info(f" structured data --> {data}")
            structured_data.append(data)
            sleep(15)  # 15 sec

        print("-------------> structured_data", structured_data)
        logger.info(f" structured_data --> {structured_data}")
        formatted_data = []
        for json_str in structured_data:
            formatted_data.extend(json.loads(json_str))

        print("Formatted structured data:", formatted_data)
        logger.info(f"Formatted structured data: {formatted_data}")
        if len(formatted_data) == 0:
            print("-------------> no data found")
            logger.info("-------------> no data found")
            return

        contact_info_list = []
        for data in formatted_data:
            if data.get("website_link"):
                print("-------------> inside website link")
                content = await scrapper.crawl_dynamic_content(data["website_link"])
                print("-------------> content", content)
                logger.info(f"-------------> content: {content}")
                page_internal_link = content.get("internal_links")
                page_external_link = content.get("external_links")

                # Extract contact-related links
                contact_links = []

                # Helper function to check links
                def check_links_for_contact(links):
                    if not links:
                        return []

                    found_links = []
                    for link in links:
                        href = link.get("href", "").lower()
                        text = link.get("text", "").lower()

                        # Check for contact-related keywords in URL or text
                        contact_keywords = ["contact", "contact-us"]
                        if any(keyword in href for keyword in contact_keywords) or any(
                            keyword in text for keyword in contact_keywords
                        ):
                            found_links.append(link["href"])
                    return found_links

                # Check both internal and external links
                contact_links.extend(check_links_for_contact(page_internal_link))
                contact_links.extend(check_links_for_contact(page_external_link))

                # Add check for empty contact_links
                if contact_links:
                    contact_content = await scrapper.crawl_dynamic_content(
                        contact_links[0]
                    )
                    print("-------------> contact_content", contact_content)
                    logger.info(f"-------------> contact_content: {contact_content}")
                    contact_info = await scrapper.get_null_data_from_content_claude(
                        contact_content.get("content"), data
                    )
                else:
                    # Handle case when no contact links are found
                    print("-------------> No contact links found")
                    logger.info("-------------> No contact links found")
                    contact_info = {}

                print("-------------> contact_info", contact_info)
                logger.info(f"-------------> contact_info: {contact_info}")
                # Update data with contact information if available
                for field in [
                    "email",
                    "phone_number",
                    "website_link",
                    "address",
                    "postcode",
                ]:
                    if contact_info.get(field):
                        data[field] = contact_info[field]

                # Add the updated data to contact_info_list
                contact_info_list.append(data)
                print("-------------> updated data:", data)
                logger.info(f"-------------> updated data: {data}")
                print("-------------> contact_info_list", contact_info_list)
                logger.info(f"-------------> contact_info_list: {contact_info_list}")
                print("formatted_data", formatted_data)
                logger.info(f"-------------> formatted_data: {formatted_data}")

            elif data.get("internal_navigation_link"):
                print("-------------> inside internal link navigation")
                logger.info("-------------> inside internal link navigation")
                contact_info = await scrapper.crawl_dynamic_content(
                    data["internal_navigation_link"]
                )
                contact_content = await scrapper.get_null_data_from_content_claude(
                    contact_info.get("content"), data
                )
                # Convert contact_content to dictionary if it's a list with one item
                if isinstance(contact_content, list) and len(contact_content) > 0:
                    contact_content = contact_content[0]

                print("-------------> contact_content", contact_content)
                logger.info(f"-------------> contact_content: {contact_content}")
                # Now safely access the dictionary
                if isinstance(contact_content, dict):
                    if contact_content.get("email"):
                        data["email"] = contact_content["email"]
                    if contact_content.get("phone_number"):
                        data["phone_number"] = contact_content["phone_number"]
                    if contact_content.get("website_link"):
                        data["website_link"] = contact_content["website_link"]
                    if contact_content.get("address"):
                        data["address"] = contact_content["address"]
                    if contact_content.get("postcode"):
                        data["postcode"] = contact_content["postcode"]

                contact_info_list.append(data)
                print("-------------> contact_content", contact_info_list)
                print("formatted_data", formatted_data)
                logger.info(f"-------------> contact_content: {contact_info_list}")
                logger.info(f"-------------> formatted_data: {formatted_data}")
            else:
                data["phone_number"] = "INTERNAL LINK NOT FOUND"

        print("-------------> contact_info_list", contact_info_list)
        logger.info(f"-------------> contact_info_list: {contact_info_list}")

        for data in formatted_data:
            if data.get("website_link"):
                print("-------------> without LLM", data["business_name"])
                logger.info("-------------> without LLM", data["business_name"])
                try:
                    # Construct potential contact page URLs
                    contact_urls = [
                        f"{data['website_link'].rstrip('/')}/contact",
                        f"{data['website_link'].rstrip('/')}/contact-us",
                        f"{data['website_link'].rstrip('/')}/contact.html",
                        f"{data['website_link'].rstrip('/')}/contact-us.html",
                        data["website_link"],
                    ]

                    for url in contact_urls:
                        contact_info = await scrapper.extract_contact_info(url)
                        if contact_info["success"]:
                            # Update data if new information is found
                            if (
                                contact_info["phone_number"]
                                and not data["phone_number"]
                            ):
                                data["phone_number"] = contact_info["phone_number"]
                            if contact_info["email"] and not data["email"]:
                                data["email"] = contact_info["email"]

                            # Break if we found both phone and email
                            if data["phone_number"] and data["email"]:
                                break

                except Exception as e:
                    print(
                        f"Error extracting contact info for {data['business_name']}: {str(e)}"
                    )
                    logger.info(
                        f"Error extracting contact info for {data['business_name']}: {str(e)}"
                    )
            elif data.get("internal_navigation_link"):
                print("-------------> LLM", data["business_name"])
                contact_info = await scrapper.crawl_dynamic_content(
                    data["internal_navigation_link"]
                )
                contact_info_structured = (
                    await scrapper.get_null_data_from_content_claude(contact_info, data)
                )
                print("LLM contact_info_structured", contact_info_structured)
                data.update(contact_info_structured)
                logger.info(f"LLM contact_info_structured: {contact_info_structured}")

        # firebase firestore
        firestore = db()

        for data in formatted_data:
            await firestore.add_data("prospects", data)
        print("end result", formatted_data)
        logger.info(f"end result: {formatted_data}")
        ex_end = perf_counter()
        execution_time = ex_end - ex_start
        print(f"Execution time {ex_end - ex_start} seconds")
        return {
            "status": "success",
            "execution_time": execution_time,
            "data": formatted_data,
        }
    except Exception as e:
        logger.error(f"Error processing location: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error processing location: {str(e)}"
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=8080)
