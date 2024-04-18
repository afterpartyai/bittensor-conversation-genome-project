import json
import os
import random
from datetime import datetime, timezone
from traceback import print_exception

#import torch


import numpy as np
#from scipy.stats import skew

from conversationgenome.Utils import Utils


class Evaluator:
    min_tags = 3
    verbose = False

    # Tag all the vectors from all the tags and return set of vectors defining the neighborhood
    async def calculate_semantic_neighborhood(self, conversation_metadata, tag_count_ceiling=None):
        all_vectors = []
        count = 0

        # Note: conversation_metadata['vectors'] is a dict, so:
        #       numeric_vectors = conversation_metadata['vectors'][tag_name]['vectors']
        for tag_name, val in conversation_metadata['vectors'].items():
            all_vectors.append(val['vectors'])
            count += 1
            if tag_count_ceiling and count > tag_count_ceiling:
                break
        if self.verbose:
            print("all_vectors",all_vectors )
        # Create a vector representing the entire content by averaging the vectors of all tokens
        if len(all_vectors) > 0:
            neighborhood_vectors = np.mean(all_vectors, axis=0)
            return neighborhood_vectors
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



    async def evaluate(self, full_convo_metadata=None, miner_results=None, body=None, exampleList=None):
        final_scores = []
        now = datetime.now(timezone.utc)
        full_conversation_neighborhood = await self.calculate_semantic_neighborhood(full_convo_metadata)
        if self.verbose:
            print("full_conversation_neighborhood vector count: ", len(full_conversation_neighborhood))
        for idx, miner_result in enumerate(miner_results):
            results = await self.calc_scores(full_convo_metadata, full_conversation_neighborhood, miner_result)
        return

        num_responses = len(miner_results)
        scores = torch.zeros(num_responses)
        zero_score_mask = torch.ones(num_responses)
        rank_scores = torch.zeros(num_responses)

        avg_ages = torch.zeros(num_responses)
        avg_age_scores = torch.zeros(num_responses)
        uniqueness_scores = torch.zeros(num_responses)
        credit_author_scores = torch.zeros(num_responses)

        max_avg_age = 0

        spot_check_id_dict = dict()

        return

        # quick integrity check and get spot_check_id_dict
        utcnow = datetime.now(timezone.utc)
        for idx, miner_response in enumerate(miner_responses):
            try:
                # Make sure there are enough tags to make processing worthwhile
                if miner_response is None or not miner_response or len(miner_response['tags']) < self.min_tags:
                    bt.logging.info(f"Only {len(miner_response['tags'])} tag(s) found for miner {miner_response['uid']}. Skipping.")
                    zero_score_mask[idx] = 0
                    continue
                diff = compare_arrays(full_convo_tags, miner_response['tags'])
                bt.logging.debug(f"uid: {miner_response['uid']} Both tag(s) count:{len(diff['both'])} / Miner unique: {diff['unique_2']} ")
            except Exception as e:
                bt.logging.error(f"Error while intitial checking {idx}-th response: {e}, 0 score")
                bt.logging.debug(print_exception(type(e), e, e.__traceback__))
                zero_score_mask[idx] = 0
            # Loop through tags that match the full convo and get the scores for those
            # These are de-emphasized -- they are more for validation
            both_tag_scores = []
            tag_count_ceiling = 5
            for tag in diff['both']:
                resp2 = await llm.simple_text_to_tags(tag, min_tokens=0)
                if len(resp2.keys()) == 0:
                    print(f"No vectors found for tag '{tag}'. Score of 0.")
                    both_tag_scores.append(0)
                    continue
                neighborhood_vector2 = await llm.get_neighborhood(resp2, tag_count_ceiling=tag_count_ceiling)
                #print("neighborhood_vector2", neighborhood_vector2)
                score = llm.score_vector_similarity(neighborhood_vector, neighborhood_vector2)
                both_tag_scores.append(score)
                print("Score", tag, score)
            if len(both_tag_scores) > 0:
                both_tag_scores_avg = np.mean(both_tag_scores)
                both_tag_scores_median = np.median(both_tag_scores)
            else:
                both_tag_scores_avg = 0.0
                both_tag_scores_median = 0.0
            # Calculate unique tags and then take to top 20
            unique_tag_scores = []
            for tag in diff['unique_2']:
                unique_tag_scores.append(self.get_full_convo_tag_score(tag))
            unique_tag_scores_avg = np.mean(unique_tag_scores)

            # TODO: Take full convo tags and generate semantic neighborhood
            # Figure out standard deviation for vectors in neighboardhood
            #       Test each unique term against neighboard -- how many SDs does term similarity score?
            # Weight score on SD similarity scores

            final_score = (both_tag_scores_avg * 0.3) + (unique_tag_scores_avg * 0.7)
            bt.logging.debug(f"Final score: {final_score} Both score avg: {both_tag_scores_avg} Unique score avg: {unique_tag_scores_avg}")
            final_scores.append(final_score)

        bt.logging.debug("Complete eval.", final_scores)

        return final_scores

    def get_full_convo_tag_score(self, tag):
        return 0.9

    async def calc_scores(self, full_convo_metadata, full_conversation_neighborhood, miner_result):
        full_convo_tags = full_convo_metadata['tags']
        tags = miner_result['tags']
        tag_vector_dict = miner_result['vectors']
        scores = []
        scores_both = []
        scores_unique = []
        tag_count_ceiling = 5
        # Remove duplicate tags
        tag_set = list(set(tags))
        diff = Utils.compare_arrays(full_convo_tags, tag_set)
        for tag in tag_set:
            is_unique = False
            if tag in diff['unique_2']:
                is_unique = True
            #print(example, resp2)
            if not tag in tag_vector_dict:
                print(f"No vectors found for tag '{tag}'. Score of 0. Unique: {is_unique}")
                scores.append(0)
                if is_unique:
                    scores_unique.append(0)
                else:
                    scores_both.append(0)
                continue
            tag_vectors = tag_vector_dict[tag]['vectors']
            score = self.score_vector_similarity(full_conversation_neighborhood, tag_vectors)
            #print("score", score)
            scores.append(score)
            if is_unique:
                scores_unique.append(score)
            else:
                scores_both.append(score)
            print(f"Score for {tag}: {score} -- Unique: {is_unique}")

        return (scores, scores_both, scores_unique)

if __name__ == "__main__":
    print("Setting up test data...")

    body = """Today for lunch, I decided to have a colorful and healthy meal. I started off with a bowl of mixed greens, topped with some cherry tomatoes, cucumbers, and sliced avocado. I love incorporating fruits and vegetables into my meals as they are packed with vitamins and minerals that are essential for our bodies. The fresh and crisp vegetables added a nice crunch to my salad, making it a refreshing and satisfying choice.
    Next, I had a grilled chicken wrap with a side of steamed broccoli. The wrap was filled with tender and juicy chicken, lettuce, tomatoes, and a drizzle of ranch dressing. It was a perfect balance of protein and veggies, making it a well-rounded meal. The steamed broccoli was a great addition as it provided a good source of fiber and other nutrients.
    To satisfy my sweet tooth, I had a bowl of mixed fruit for dessert. It had a variety of fruits such as strawberries, blueberries, and grapes. Not only did it add some natural sweetness to my meal, but it also provided me with a boost of antioxidants and other beneficial nutrients.
    Eating a nutritious and balanced lunch not only keeps me physically healthy but also helps me stay focused and energized for the rest of the day. It's important to make conscious choices and incorporate fruits and vegetables into our meals to maintain a healthy diet. After finishing my lunch, I felt satisfied and ready to tackle the rest of my day with a renewed sense of energy."""

    tagLists = [
        # Mostly relevant, with a few irrelevant tags
        ["apple", "lunch", "automobile", "banana", "pear", "dinner", "meal", "beef", "akjsdkajsdlkajl", "political party", "airliner"],
        # Tags close to target
        ["apple", "lunch", "banana", "pear", "dinner", "meal", "beef", "desert", "broccoli", "strawberries"],
        # Few tags, all irrelevant
        ["akjsdkajsdlkajl", "political party", "airliner"],
        # Many tags, all irrelevant
        ["aircraft", "aviation", "flight", "passengers", "pilots", "cockpit", "air traffic control", "takeoff", "landing", "jet engines", "altitude", "airlines", "airports", "flight attendants", "airplane mode", "airworthiness", "boarding", "turbulence", "emergency exits", "cabin crew"],
        # Food tags, not directly related to ground text (lunch)
        ["fruit", "apple", "orange", "banana", "grape", "strawberry", "mango", "watermelon", "pineapple", "kiwi", "peach", "plum", "cherry", "pear", "blueberry", "raspberry", "lemon", "lime", "fig", "coconut"],
        # Meal tags
        ["lunch", "food", "meal", "dining", "restaurant", "sandwich", "salad", "soup", "fast food", "takeout", "brunch", "picnic", "cafeteria", "lunch break", "healthy", "comfort food", "bag lunch", "leftovers", "vegetarian", "gluten-free"],
        # Duplicate tags and 1 irrelevant tags -- so 2 tags, 1 relevant and 1 irrelevant
        ["apple", "apple", "apple", "apple", "apple", "apple", "apple", "apple", "apple", "apple", "apple", "apple", "apple", "apple", "akjsdkajsdlkajl"],
        # Many non-sense tags (no latent space location) and 1 very relevant tag
        ["apple", "akjsdkajsdlkajl1", "akjsdkajsdlkajl2", "akjsdkajsdlkajl3", "akjsdkajsdlkajl4", "akjsdkajsdlkajl5", "akjsdkajsdlkajl6", "akjsdkajsdlkajl7", "akjsdkajsdlkajl8"],
        # Many non-sense tags (no latent space location) and 1  irrelevant tag
        ["clock", "akjsdkajsdlkajl1", "akjsdkajsdlkajl2", "akjsdkajsdlkajl3", "akjsdkajsdlkajl4", "akjsdkajsdlkajl5", "akjsdkajsdlkajl6", "akjsdkajsdlkajl7", "akjsdkajsdlkajl8"],
    ]
    miner_tag_lists = tagLists

    async def calculate_penalty(score, num_tags, num_unique_tags,  min_score, max_score):
        final_score = score
        # All junk tags. Penalize
        if max_score < .2:
            final_score *= 0.5
        # Very few tags. Penalize.
        if num_tags < 2:
            final_score *= 0.2
        if num_unique_tags < 1:
            final_score *= 0.3
        return score

    async def calculate_final_scores(ground_tags, miner_tag_lists):
        e = Evaluator()
        # Find the max tags returned for the y-axis of the plot
        max_len = len(max(miner_tag_lists, key=len))
        print("max_len", max_len)
        scoreData = []
        for idx, tags in enumerate(miner_tag_lists):
            print(f"\n\n__________________ User {idx} __________________")
            skewness = 0
            results = await e.calc_scores(ground_tags, neighborhood_vector, tags)
            (scores, scores_both, scores_unique) = results

            mean_score = np.mean(scores)
            median_score = np.median(scores)
            freq, bins = np.histogram(scores, bins=10, range=(0,1))
            #skewness = skew(freq)
            skewness = skew(scores)
            min_score = np.min(scores)
            max_score = np.max(scores)


            #y1 =  sorted(scores)
            #print(scores)
            freq, bins = np.histogram(scores, bins=10, range=(0,1))
            mean = np.mean(scores)
            std = np.std(scores)
            plt.plot(bins[:-1], freq)
            plt.axvline(mean, color='r', linestyle='--', label='Mean')
            plt.axvline(mean + std, color='g', linestyle='--', label='1 Standard Deviation')
            plt.axvline(mean - std, color='g', linestyle='--')

            # Adjust the skewness so 0 is in the center of the graph
            skewness_x = 0.5 + (0.3 * skewness)
            plt.axvline(skewness_x, color='b', linestyle='--', label='Skewness')

            plt.xlabel('Values')
            plt.ylabel('Frequency')
            plt.legend()
            plt.ylim(0,max_len)

            #y1 =  scores
            #plt.plot(x, y1, label="line L")
            #plt.plot()

            plt.title(f"Scores for {idx} user")
            plt.show()

            # SCORING FUNCTION
            adjusted_score = (
                (0.7 * median_score) +
                (0.3 * mean_score)
            ) / 2
            final_score = await calculate_penalty(adjusted_score, len(scores), len(scores_unique), min_score, max_score)

            scoreData.append({"uid": idx, "adjustedScore":adjusted_score, "final_score":final_score, "tags":tags})

            print(f"__________Tags: {len(tags)} Unique Tags: {len(scores_unique)} Median score: {median_score} Mean score: {mean_score} Skewness: {skewness} Min: {min_score} Max: {max_score}" )
        print("Complete. Score sets:")
        scoreData = sort_dict_list(scoreData, "adjustedScore", ascending=False)
        Code(json.dumps(scoreData, indent=4))
        #render_json()

    print("Running basic spacy keyword test...")
    llm = llm_spacy()
    #response = await llm.simple_text_to_tags(body, min_tokens=0)
    ground_tags = list(response.keys())
    print(f"Found tags for main conversation: {ground_tags}")
    #neighborhood_vector = await llm.get_neighborhood(response)
    #print("neighborhood_vector", neighborhood_vector)
    print("Processing tag sets...")
    #await calculate_final_scores(ground_tags, miner_tag_lists)