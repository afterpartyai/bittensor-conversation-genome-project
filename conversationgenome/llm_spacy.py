import json

spacy = None
Matcher = None
try:
    import spacy
    from spacy.matcher import Matcher
except:
    print("Please install spacy to run locally")
    # en_core_web_sm model vectors = 96 dimensions.
    # en_core_web_md and en_core_web_lg = 300 dimensions
    # python -m spacy download en_core_web_sm
    # python -m spacy download en_core_web_lg

class llm_spacy:
    nlp = None
    verbose = False

    def get_nlp(self):
        nlp = self.nlp
        dataset = "en_core_web_lg"  # ~600mb
        if not nlp:
            # Manual download
            # python -m spacy download en_core_web_sm
            # Faster small and medium models:
            # en_core_web_sm and en_core_web_md

            if not spacy.util.is_package(dataset):
                print(f"Downloading spacy model {dataset}...")
                spacy.cli.download(dataset)
                print("Model {dataset} downloaded successfully!")

            nlp = spacy.load(dataset) # ~600mb
            print(f"Spacy {dataset} Vector dimensionality: {nlp.vocab.vectors_length}")
            self.nlp = nlp
        return nlp

    async def simple_text_to_tags(self, body, min_tokens=5):
        nlp = self.get_nlp()

        # Define patterns
        adj_noun_pattern = [{"POS": "ADJ"}, {"POS": "NOUN"}]
        pronoun_pattern = [{"POS": "PRON"}]
        unique_word_pattern = [{"POS": {"IN": ["NOUN", "VERB", "ADJ"]}, "IS_STOP": False}]

        # Initialize the Matcher with the shared vocabulary
        matcher = Matcher(nlp.vocab)
        matcher.add("ADJ_NOUN_PATTERN", [adj_noun_pattern])
        matcher.add("PRONOUN_PATTERN", [pronoun_pattern])
        matcher.add("UNIQUE_WORD_PATTERN", [unique_word_pattern])

        doc = nlp( body )
        if self.verbose:
            print("DOC", doc)
        matches = matcher(doc)
        matches_dict = {}
        for match_id, start, end in matches:
            span = doc[start:end]
            if self.verbose:
                print("Span text", span.text)
            matchPhrase = span.lemma_
            if len(matchPhrase) > min_tokens:
                if self.verbose:
                    print(f"Original: {span.text}, Lemma: {span.lemma_} Vectors: {span.vector.tolist()}")
                if not matchPhrase in matches_dict:
                    matches_dict[matchPhrase] = {"tag":matchPhrase, "count":0, "vectors":span.vector.tolist()}
                matches_dict[matchPhrase]['count'] += 1

        return matches_dict

    async def get_neighborhood(self, response, tag_count_ceiling=None):
        all_vectors = []
        count = 0
        for key, val in response.items():
            all_vectors.append(val['vectors'])
            count += 1
            if tag_count_ceiling and count > tag_count_ceiling:
                break
        if self.verbose:
            print("all_vectors",all_vectors )
        # Create a vector representing the entire content by averaging the vectors of all tokens
        if len(all_vectors) > 0:
            neighborhood_vector = np.mean(all_vectors, axis=0)
            return neighborhood_vector
        else:
            return None

    def score_vector_similarity(self, neighborhood_vectors, individual_vectors):
        # Calculate the similarity score between the neighborhood_vectors and the individual_vectors
        # If all vectors are 0.0, the vector wasn't found for scoring in the embedding score
        if np.all(individual_vectors==0):
            return 0
        # Calculate the cosine similarity between two sets of vectors
        similarity_score = np.dot(neighborhood_vectors, individual_vectors) / (np.linalg.norm(neighborhood_vectors) * np.linalg.norm(individual_vectors))
        #print(f"Similarity score between the content and the tag: {similarity_score}")
        return similarity_score



    async def conversation_to_metadata(self,  convo):
        # For this simple matcher, just munge all of the lines together
        body = json.dumps(convo['lines'])
        matches_dict = await self.simple_text_to_tags(body)
        return {"tags": matches_dict}

