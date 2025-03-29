import spacy
from spanbert import SpanBERT
from spacy_help_functions import get_entities, create_entity_pairs

def spanbert_processing(candidate_pairs):
    
    # Load pre-trained SpanBERT model
    spanbert = SpanBERT("./pretrained_spanbert")
    relation_preds = spanbert.predict(candidate_pairs)  # get predictions: list of (relation, confidence) pairs

    # Print Extracted Relations
    print("\nExtracted relations:")
    for ex, pred in list(zip(candidate_pairs, relation_preds)):
        print("\tSubject: {}\tObject: {}\tRelation: {}\tConfidence: {:.2f}".format(ex["subj"][0], ex["obj"][0], pred[0], pred[1]))

        # TODO: focus on target relations
        # '1':"per:schools_attended"
        # '2':"per:employee_of"
        # '3':"per:cities_of_residence"
        # '4':"org:top_members/employees"