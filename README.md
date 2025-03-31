# tag-youre-it
COMS 6111 Project 2

## Group
Helena He (hh3090) <br>
Kristine Pham (klp2157)

## Files
- main.py
- gemini.py
- spanbert_process.py
- README.md

## To Run the Program:
```
python3 main.py [-spanbert|-gemini] <google api key> <google engine id> <google gemini api key> <r> <t> <q> <k>
```

## Project Design

### Code Structure


### Externel Libraries

## Step 3 Description
For each unprocessed URL, we start by calling the `extract_plain_text()` function. It will:

1. Send an HTTP GET request with a timeout of 10 seconds to fetch the webpage.
2. Once the webpage is successfully retrieved, use BeautifulSoup to parse the HTML and remove unnecessary elements such as scripts, styles, headers, footers, navigation, and aside tags.
3. Extract the plain text from the HTML, replace tabs and newlines with spaces, and reduce multiple spaces to a single space.
4. Finally, if the resulting text exceeds the maximum length (10,000 characters), truncate it accordingly and returns the final plain text.

Next, the `extract_relations()` function is called. It will:

1. Iterate over every sentence in the document and generate candidate entity pairs using a helper function called `create_entity_pairs()`. 
2. For each entity pair, create two possible orderings. The first ordering will have the first entity as the subject and the second entity as the object. The second ordering will have the first entity as the object and the second entity as the subject.
3. Filter these candidate pairs to only include those that match the specified target relation requirement for the subject and object types. 
4. If any valid candidate pairs are found, extract relations using one of two extraction methods: SpanBERT or Gemini.

For SpanBERT:


For Gemini, a function called `extract_relations_gemini()` is called. It will:

1. Configure the generative AI library with the provided API key. 
2. Construct a prompt using one-shot learning that includes an example output, an example sentence, and instructions for extracting instances of the target relation. The output should be a list of lists, where each inner array is formatted as ["Subject: {subj_type}", "{relation}", "Object: {obj_type}"].
3. Call the `get_gemini_completion()` helper function with the constructed prompt to generate a response from Gemini for the prompt.
4. If the request fails, use an exponential backoff retry mechanism with a maximum of five retries and added random jitter to avoid resource exhaustion. 
5. Once a successful response is obtained (or the retries are exhausted), parse the response using the `parse_response_text()` helper function. 
6. Add all parsed relations to the results set.
7. Add a short pause before returning to ensure that the extraction process does not overload the API.

## Google Custom Search Engine
