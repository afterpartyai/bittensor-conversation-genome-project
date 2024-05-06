import json
import os
import random
from datetime import datetime, timezone
from traceback import print_exception

verbose = False
torch = None
try:
    import torch
except:
    bt.logging.info("torch not installed")


import numpy as np

from conversationgenome.utils.Utils import Utils
from conversationgenome.mock.MockBt import MockBt

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()



class Evaluator:
    min_tags = 3
    verbose = False
    scoring_factors = {
        "top_3_mean": 0.5,
        "median_score": 0.2,
        "mean_score": 0.2,
        "max_score": 0.1,
    }

    # Tag all the vectors from all the tags and return set of vectors defining the neighborhood
    async def calculate_semantic_neighborhood(self, conversation_metadata, tag_count_ceiling=None):
        all_vectors = []
        count = 0

        # Note: conversation_metadata['vectors'] is a dict, so:
        #       numeric_vectors = conversation_metadata['vectors'][tag_name]['vectors']
        for tag_name, val in conversation_metadata['vectors'].items():
            all_vectors.append(val['vectors'])
            #all_vectors.append(val)
            count += 1
            if tag_count_ceiling and count > tag_count_ceiling:
                break
        if self.verbose:
            bt.logging.info("all_vectors",all_vectors )
        # Create a vector representing the entire content by averaging the vectors of all tokens
        if len(all_vectors) > 0:
            neighborhood_vectors = np.mean(all_vectors, axis=0)
            return neighborhood_vectors
        else:
            return None

    def score_vector_similarity(self, neighborhood_vectors, individual_vectors):
        similarity_score = 0
        # Calculate the similarity score between the neighborhood_vectors and the individual_vectors
        # If all vectors are 0.0, the vector wasn't found for scoring in the embedding score
        if np.all(individual_vectors==0):
            bt.logging.error("All empty vectors")
            return 0
        # Calculate the cosine similarity between two sets of vectors
        try:
            similarity_score = np.dot(neighborhood_vectors, individual_vectors) / (np.linalg.norm(neighborhood_vectors) * np.linalg.norm(individual_vectors))
        except:
            bt.logging.error("Error generating similarity_score. Setting to zero.")
        bt.logging.debug(f"Similarity score between the content and the tag: {similarity_score}")
        return similarity_score



    async def evaluate(self, full_convo_metadata=None, miner_responses=None, body=None, exampleList=None, verbose=None):
        if verbose == None:
            verbose = self.verbose
        #bt.logging.info("FULL convo tags", full_convo_metadata['tags'])
        final_scores = []
        now = datetime.now(timezone.utc)
        full_conversation_neighborhood = await self.calculate_semantic_neighborhood(full_convo_metadata)
        if verbose:
            bt.logging.info("full_conversation_neighborhood vector count: ", len(full_conversation_neighborhood))

        num_responses = len(miner_responses)
        scores = torch.zeros(num_responses)
        zero_score_mask = torch.ones(num_responses)
        rank_scores = torch.zeros(num_responses)
        bt.logging.info(f"DEVICE for rank_scores: {rank_scores.device}")

        avg_ages = torch.zeros(num_responses)
        avg_age_scores = torch.zeros(num_responses)
        uniqueness_scores = torch.zeros(num_responses)
        credit_author_scores = torch.zeros(num_responses)

        max_avg_age = 0

        spot_check_id_dict = dict()


        final_scores = []
        for idx, response in enumerate(miner_responses):
            if not response.cgp_output:
                bt.logging.info(f"BAD RESPONSE: {idx} HOTKEY: {response.axon.hotkey}")
                final_scores.append({"uuid": response.axon.uuid, "hotkey": response.axon.hotkey, "adjustedScore":0.0, "final_miner_score":0.0})
            else:
                #bt.logging.info("GOOD RESPONSE", idx, response.axon.uuid, response.axon.hotkey, )
                miner_result = response.cgp_output[0]
                try:
                    # Make sure there are enough tags to make processing worthwhile
                    if miner_result is None or not miner_result or len(miner_result['tags']) < self.min_tags:
                        bt.logging.info(f"Only {len(miner_result['tags'])} tag(s) found for miner {miner_result['uid']}. Skipping.")
                        zero_score_mask[idx] = 0
                        continue
                except Exception as e:
                    bt.logging.error(f"Error while intitial checking {idx}-th response: {e}, 0 score")
                    bt.logging.debug(print_exception(type(e), e, e.__traceback__))
                    zero_score_mask[idx] = 0

                # Loop through tags that match the full convo and get the scores for those
                results = await self.calc_scores(full_convo_metadata, full_conversation_neighborhood, miner_result)

                (scores, scores_both, scores_unique) = results
                mean_score = np.mean(scores)
                median_score = np.median(scores)
                min_score = np.min(scores)
                max_score = np.max(scores)
                std = np.std(scores)
                sorted_scores = np.sort(scores)
                top_3_mean = np.mean(sorted_scores[-3:])

                scoring_factors = self.scoring_factors
                adjusted_score = (
                    (scoring_factors['top_3_mean'] * top_3_mean)+
                    (scoring_factors['median_score'] * median_score) +
                    (scoring_factors['mean_score'] * mean_score) +
                    (scoring_factors['max_score'] * max_score)
                )

                final_miner_score = adjusted_score #await calculate_penalty(adjusted_score,both ,unique, min_score, max_score)
                final_scores.append({"uid": idx+1, "uuid": response.axon.uuid, "hotkey": response.axon.hotkey, "adjustedScore":adjusted_score, "final_miner_score":final_miner_score})
                bt.logging.debug(f"_______ {adjusted_score} ___Num Tags: {len(miner_result['tags'])} Unique Tag Scores: {scores_unique} Median score: {median_score} Mean score: {mean_score} Top 3 Mean: {top_3_mean} Min: {min_score} Max: {max_score}" )


        bt.logging.debug("Complete evalulation. Final scores: {final_scores}")
        # Force to use cuda if available -- otherwise, causes device mismatch
        rank_scores = rank_scores.to('cuda')
        # Convert to tensors
        for idx, final_score in enumerate(final_scores):
            rank_scores[idx] = final_scores[idx]['adjustedScore']
        return (final_scores, rank_scores)

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
        bt.logging.debug(f"Calculating scores for tag_set: {tag_set}")
        for tag in tag_set:
            is_unique = False
            if tag in diff['unique_2']:
                is_unique = True
            #bt.logging.info(example, resp2)
            if not tag in tag_vector_dict:
                bt.logging.error(f"No vectors found for tag '{tag}'. Score of 0. Unique: {is_unique}")
                scores.append(0)
                if is_unique:
                    scores_unique.append(0)
                else:
                    scores_both.append(0)
                continue
            tag_vectors = tag_vector_dict[tag]['vectors']
            score = self.score_vector_similarity(full_conversation_neighborhood, tag_vectors)
            scores.append(score)
            if is_unique:
                scores_unique.append(score)
            else:
                scores_both.append(score)
            bt.logging.debug(f"Score for '{tag}': {score} -- Unique: {is_unique}")
        bt.logging.info(f"Scores num: {len(scores)} num of Unique tags: {len(scores_unique)} num of full convo tags: {len(full_convo_tags)}")

        return (scores, scores_both, scores_unique)

if __name__ == "__main__":
    bt.logging.info("Setting up test data...")

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

    async def calculate_penalty(uid, score, num_tags, num_unique_tags, min_score, max_score):
        final_score = score

        # All junk tags. Penalize
        if max_score < .2:
            bt.logging.debug("calculate_penalty: all junk tag")
            final_score *= 0.5

        # Very few tags. Penalize.
        if num_tags < 2:
            bt.logging.debug("calculate_penalty: very few tags")
            final_score *= 0.2

        # no unique tags. Penalize
        if num_unique_tags < 1:
            bt.logging.debug("calculate_penalty: less than 1 unique tag")
            final_score *= 0.75
        elif num_unique_tags < 2:
            bt.logging.debug("calculate_penalty: less than 2 unique tags")
            final_score *= 0.8
        elif num_unique_tags < 3:
            bt.logging.debug("calculate_penalty: less than 3 unique tags")
            final_score *= 0.85
        elif num_unique_tags < 4:
            bt.logging.debug("calculate_penalty: less than 4 unique tags")
            final_score *= 0.9
        elif num_unique_tags < 5:
            bt.logging.debug("calculate_penalty: less than 5 unique tags")
            final_score *= 0.95

        return final_score

    async def calculate_final_scores(ground_tags, miner_tag_lists):
        e = Evaluator()
        # Find the max tags returned for the y-axis of the plot
        max_len = len(max(miner_tag_lists, key=len))
        bt.logging.info("max_len", max_len)
        scoreData = []
        for idx, tags in enumerate(miner_tag_lists):
            bt.logging.info(f"\n\n__________________ User {idx} __________________")
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
            #bt.logging.info(scores)
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

            bt.logging.info(f"__________Tags: {len(tags)} Unique Tags: {len(scores_unique)} Median score: {median_score} Mean score: {mean_score} Skewness: {skewness} Min: {min_score} Max: {max_score}" )
        bt.logging.info("Complete. Score sets:")
        scoreData = sort_dict_list(scoreData, "adjustedScore", ascending=False)
        Code(json.dumps(scoreData, indent=4))
        #render_json()

    bt.logging.info("Running basic spacy keyword test...")
    llm = llm_spacy()
    #response = await llm.simple_text_to_tags(body, min_tokens=0)
    ground_tags = list(response.keys())
    bt.logging.info(f"Found tags for main conversation: {ground_tags}")
    #neighborhood_vector = await llm.get_neighborhood(response)
    #bt.logging.info("neighborhood_vector", neighborhood_vector)
    bt.logging.info("Processing tag sets...")
    #await calculate_final_scores(ground_tags, miner_tag_lists)