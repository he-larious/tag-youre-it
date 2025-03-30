import spacy
from spanbert import SpanBERT
from spacy_help_functions import get_entities, create_entity_pairs

# 1) updated results (in a list or dictionary)
# 2) updated count of total extractions (including the duplicates)
def extract_relations_spanbert(spanbert, candidate_pairs, input_tokens, results, total_extracted, t, target_r):
    relation_preds = spanbert.predict(candidate_pairs)  # get predictions: list of (relation, confidence) pairs

    total_extracted += len(relation_preds)

    # Print Extracted Relations
    for ex, pred in list(zip(candidate_pairs, relation_preds)):
        # check if relation is target
        if target_r != pred[0]:
            continue
        
        print("\t\t=== Extracted Relation ===")
        confidence = pred[1]
        subj = ex['subj'][0]
        obj = ex['obj'][0]

        print(f"\t\tInput tokens: {input_tokens}")
        print(f"\t\tOutput Confidence: {confidence} ; Subject: {subj} ; Object: {obj} ;")

        # results = {(subj, obj): confidence, ..., (subj, obj): confidence} 

        if confidence < t:
            print("\t\tConfidence is lower than threshold confidence. Ignoring this.")

        elif (subj, obj) in results and confidence < results[(subj, obj)]:
            print("\t\tDuplicate with lower confidence than existing record. Ignoring this.")

        # otherwise, add to results
        else:
            results[(subj, obj)] = confidence
            print("Adding to set of extracted relations")
        print("\t\t==========")
    print("\n")
    return results, total_extracted
