import requests
from bs4 import BeautifulSoup
import openai
from urllib.parse import urljoin, urlparse
import re

# Configure OpenAI API Key
openai.api_key = "your_openai_api_key"
def chunk_text(text, chunk_size=1000):
    """Splits text into manageable chunks."""
    words = text.split()
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    return chunks

def is_valid_url(url):
    """Checks if a URL is valid."""
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def scrape_website(url, chunk_size=1000):
    """Scrapes the given website deeply and returns all structured content."""
    try:
        # Send the initial request
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Base domain to resolve relative links
        base_domain = "{0.scheme}://{0.netloc}".format(urlparse(url))

        # Metadata
        title = soup.title.string if soup.title else "No Title Found"
        description = (
            soup.find("meta", attrs={"name": "description"}) or
            soup.find("meta", attrs={"property": "og:description"})
        )
        description = description["content"] if description else "No Description Found"
        keywords = soup.find("meta", attrs={"name": "keywords"})
        keywords = keywords["content"] if keywords else "No Keywords Found"

        # Clean unwanted tags
        for unwanted in soup(["script", "style", "noscript", "iframe", "img", "video"]):
            unwanted.decompose()

        # Extract Navigation Bar (if any)
        navbar = soup.find("nav")
        navbar_text = navbar.get_text(separator="\n", strip=True) if navbar else "No Navigation Bar Found"

        # Extract Main Div Content
        divs = soup.find_all("div")
        div_texts = [div.get_text(separator="\n", strip=True) for div in divs]
        full_div_content = "\n\n".join(div_texts)

        # Extract Links (deep links)
        links = []
        for a_tag in soup.find_all("a", href=True):
            full_url = urljoin(base_domain, a_tag["href"])
            if is_valid_url(full_url):
                links.append(full_url)
        links = list(set(links))  # Remove duplicates

        # Extract Main Content
        text_content = soup.get_text(separator="\n", strip=True)

        # Chunk text content
        text_chunks = chunk_text(text_content, chunk_size)

        # Structure all scraped data
        scraped_data = {
            "title": title,
            "description": description,
            "keywords": keywords,
            "navbar": navbar_text,
            "div_content": full_div_content,
            "text_chunks": text_chunks,
            "deep_links": links,
        }
        return scraped_data

    except requests.exceptions.RequestException as e:
        return {"error": f"HTTP Request failed: {e}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}

def chat_with_scraped_data(scraped_data, user_query):
    """Generates chatbot response based on comprehensive scraped data."""
    if "error" in scraped_data:
        return f"Error while scraping: {scraped_data['error']}"

    # Construct prompt using all scraped data
    context = (
        f"Title: {scraped_data['title']}\n"
        f"Description: {scraped_data['description']}\n"
        f"Keywords: {scraped_data['keywords']}\n"
        f"Navigation Bar: {scraped_data['navbar']}\n"
        f"Main Div Content: {scraped_data['div_content'][:1000]}...\n"
        f"Content Snippet: {scraped_data['text_chunks'][0] if scraped_data['text_chunks'] else 'No Content Found'}\n"
        f"Deep Links: {', '.join(scraped_data['deep_links'][:5])}\n"
    )
    prompt = (
        f"The following is the context extracted from the website:\n\n{context}\n\n"
        f"User Query: {user_query}\n\n"
        f"Provide a precise, accurate, and helpful response based on the above information."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant with expertise in website content analysis."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message["content"]
    except openai.error.OpenAIError as e:
        return f"Error while generating response: {e}"

if __name__ == "__main__":
    print("Welcome to the Chatbot! Let's talk 😊")
    print("You can ask questions based on the website content.")
    print("Type 'exit' anytime to end the conversation.\n")

    website_url = input("Bot: Please enter the website URL to fetch information from: ")
    print("Bot: Fetching and processing the website content...\n")

    # Scrape website data
    scraped_data = scrape_website(website_url)

    if "error" in scraped_data:
        print(f"Bot: {scraped_data['error']}")
    else:
        print("Bot: Website content fetched successfully! You can now ask questions.")

        # Chat loop
        while True:
            user_query = input("\nYou: ")
            if user_query.lower() == 'exit':
                print("Bot: It was great chatting with you! Goodbye! 👋")
                break

            print("Bot: Let me think for a moment...")
            response = chat_with_scraped_data(scraped_data, user_query)
            print(f"\nBot: {response}")
