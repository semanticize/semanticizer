from core import LinksProcessor
import collections


class MultipleEntityFeaturesProcessor(LinksProcessor):

    def process(self, links, text, settings):
        self.link_dict = {}
        self.labels = []

        if 'multi' not in settings:
            return (links, text, settings)

        # First run through links to fill dict
        for link in links:
            self.link_dict.setdefault(link['id'], []) \
                .append([link['label'], link['senseProbability'],
                        link['priorProbability'], link['linkProbability']])
            self.labels.append(link['label'])
            link['features'] = {}

        # Second run to calculate features
        for link in links:
            if 'tier1' in settings['multi']:
                features = self.FEATURE_tier_one_overlap(link, self.labels)
                link['features'].update(features)
            if 'outlinks' in settings['multi']:
                features = self.FEATURE_linked_entity_overlap(link['label'],
                                                              link['OutLinks'],
                                                              'outlinks')
                link['features'].update(features)
            if 'inlinks' in settings['multi']:
                features = self.FEATURE_linked_entity_overlap(link['label'],
                                                              link['InLinks'],
                                                              'inlinks')
                link['features'].update(features)

        return (links, text, settings)

    def FEATURE_tier_one_overlap(self, link, labels):
        """
        Perform simple 'list intersect'
        To find matching labels of candidate
        """

        tier_one = [link['title']] + [label['title'] for label in \
                    link['Labels']]
        tier_one = [(anchor, link['id']) for anchor in \
                    list((collections.Counter(tier_one) & \
                    collections.Counter(self.labels)).elements())]

        return_list = []
        for l, i in tier_one:

            if i in self.link_dict:
                for label, senseProb, priorProb, cmns in self.link_dict[i]:
                    if label == anchor:
                        return_list.append((l, i, senseProb, priorProb, cmns))
        if return_list:
            return self.calculate_features(return_list, 1, 'tier_one')

        else:
            return {}

    def FEATURE_linked_entity_overlap(self, current_label, linked_entities,
                                      features):
        """
        IN: json of {in,out}-link_ids
        Check if they occur in doc dict
        if they do, see if they are referred to
        by a different label.
        """

        # Find stuff
        result_list = []
        for link in linked_entities:
            if link['id'] in self.link_dict:
                link_label = self.link_dict[link['id']]
                for sub_link in link_label:
                    if current_label != sub_link[0]:
                        result_list.append((sub_link[0], link['id'],
                                            sub_link[1], sub_link[2],
                                            sub_link[3]))
        # Calculate features
        if result_list:
            return self.calculate_features(result_list, len(linked_entities),
                                           features)
        else:
            return {}

    def calculate_features(self, results, max_entities, features):
        """
        Given result list in format:
        label, wiki_id, senseProb, priorProb, commonness
        'Unzip' lists and create feature vectors.
        """

        label_list, id_list, sense_list, prior_list, cmns_list = \
            ([l for l, w, s, p, c in results],
             [w for l, w, s, p, c in results],
             [s for l, w, s, p, c in results],
             [p for l, w, s, p, c in results],
             [c for l, w, s, p, c in results])

        if features == 'outlinks':
            PREFIX = 'ME_OUT_'
        elif features == 'inlinks':
            PREFIX = 'ME_IN_'
        elif features == 'tier_one':
            PREFIX = 'ME_T1_'

        return {PREFIX + 'label_overlap': len(label_list),
                PREFIX + 'label_unique': len(set(label_list)),
                PREFIX + 'entity_overlap': len(id_list),
                PREFIX + 'entity_unique': len(set(id_list)),
                PREFIX + 'entity_proportion': float(len(set(id_list))) / \
                                              float(max_entities),
                PREFIX + 'sense_prob_sum': sum(sense_list),
                PREFIX + 'prior_prob_sum': sum(prior_list),
                PREFIX + 'cmns_sum': sum(cmns_list)}
