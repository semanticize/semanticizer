// # UvA Semanticizer Web API
// 
// The UvA Semanticizer Web API is a web service for semantic linking
// created in 2012 by [Daan Odijk](http://staff.science.uva.nl/~dodijk/) at
// [ILPS](http://ilps.science.uva.nl/) (University of Amsterdam). 
// This project since received contributions from (in alphabetical order): 
// [Lars Buitinck](http://staff.science.uva.nl/~buitinck/), 
// [David Graus](http://graus.nu/), 
// [Tom Kenter](http://staff.science.uva.nl/~tkenter1/), 
// [Evert Lammerts](http://www.evertlammerts.nl/), 
// [Edgar Meij](http://edgar.meij.pro/), 
// [Daan Odijk](http://staff.science.uva.nl/~dodijk/), 
// [Anne Schuth](http://www.anneschuth.nl/) and 
// [Isaac Sijaranamual](http://nl.linkedin.com/pub/isaac-sijaranamual/).
// 
// The algorithms for this webservice are developed for and described in a
// OAIR2013 publication on [Feeding the Second Screen](http://ilps.science.uva.nl/biblio/feeding-second-screen-semantic-linking-based-subtitles) by 
// [Daan Odijk](http://staff.science.uva.nl/~dodijk/), 
// [Edgar Meij](http://edgar.meij.pro/) and 
// [Maarten de Rijke](http://staff.science.uva.nl/~mdr/). 
// Part of this research was inspired by earlier ILPS publications: 
// [Adding Semantics to Microblog Posts](http://ilps.science.uva.nl/biblio/adding-semantics-microblog-posts) 
// and [Mapping Queries To The Linking Open Data Cloud](http://ilps.science.uva.nl/node/889).
// If you use this webservice for your own research, please include a reference 
// to any of these articles.
// 
// The [code](https://github.com/semanticize/semanticizer/) is released under 
// LGPL license. If you have any questions, contact 
// [Daan](http://staff.science.uva.nl/~dodijk/).
// Currently an access key for the webservice is not needed.
//
// This documents describes how to use the Semanticizer Web API. This 
// [REST](http://en.wikipedia.org/wiki/Representational_state_transfer)-like 
// web service returns [JSON](http://www.json.org/) 
// and is exposed to public at: http://semanticize.uva.nl/api/.
//
// The documentation gives examples of HTTP calls, that you could use from e.g.:
// command line using [cURL](http://en.wikipedia.org/wiki/CURL): 
// `$ curl "http://semanticize.uva.nl/api/"` or 
// using [jQuery.ajax()](http://api.jquery.com/jQuery.ajax/) in 
// [JavaScript](http://en.wikipedia.org/wiki/JavaScript). 
//
// ***

// ## Semanticizer Web API
//
// Let's have a look at the Web API. We'll send a short text to the webservice
// using the Web API. The text can also be sent as the body of a
// [HTTP POST](http://en.wikipedia.org/wiki/POST_%28HTTP%29) call. 
// Below is response of the Web API and the URL, specifying that we have a short 
// Dutch text and that we want the output to be *pretty* (i.e. human readable).
// > http://semanticize.uva.nl/api/nl?text=UvA&pretty
{
    "text": "UvA",
    "status": "OK",
    "links": [
        {
            "id": 14815,
            "text": "UvA", 
            "label": "UvA", 
            "title": "Universiteit van Amsterdam", 
            "url": "http://nl.wikipedia.org/wiki/Universiteit%20van%20Amsterdam", 
            "linkProbability": 0.2946058091286307, 
            "priorProbability": 1.0, 
            "senseProbability": 0.2946058091286307 
        }
    ]
}
// What is returned is a JSON object containing the original text, a `status` message 
// and a list of links. The only link detected in this short text is a link to the
// [Wikipedia page of the UvA](http://nl.wikipedia.org/wiki/Universiteit%20van%20Amsterdam).
//
// Every link has a number of properties, including the part of the text based on 
// which the link is made (`text` and `label`, see Normalization below), the title 
// of the target Wikipedia page (`title`) and a `url` for that page. 
// 
// Finally, each link has three heuristic measures that estimate the likelihood of
// a link being correct for the `label`: `priorProbability`, `linkProbability` and 
// `senseProbability`. How these three measures are computed will be discussed 
// below. 

// ***

// ### Counts and Heuristics
// 
// To understand how the three heuristics measures are computed we first look
// at the raw numbers from which these are computed, by adding counts to the
// API call:
// 
// > http://semanticize.uva.nl/api/nl?text=UvA&pretty&counts
{
    "text": "UvA", 
    "status": "OK",
    "links": [
        {
            "id": 14815, 
            "text": "UvA", 
            "label": "UvA", 
            "title": "Universiteit van Amsterdam", 
            "url": "http://nl.wikipedia.org/wiki/Universiteit%20van%20Amsterdam", 
            "linkProbability": 0.2946058091286307, 
            "priorProbability": 1.0, 
            "senseProbability": 0.2946058091286307, 
            "docCount": 241,
            "occCount": 326, 
            "linkDocCount": 71, 
            "linkOccCount": 75, 
            "senseDocCount": 71, 
            "senseOccCount": 75 
        }
    ]
}
// We now have four new properties for the link:
//
// * `occCount` is the number of times the `label` appears on Wikipedia
// * `docCount` is the number of documents in which the `label` appears on Wikipedia
// * `linkOccCount` is the number of times the `label` appears as 
//    [anchor](http://en.wikipedia.org/wiki/HTML_anchor#Anchor) 
//    text for a link on Wikipedia
// * `linkDocCount` is the number of documents in which the `label` appears as 
//    [anchor](http://en.wikipedia.org/wiki/HTML_anchor#Anchor) 
//    text for a link on Wikipedia
// * `senseOccCount` is the number of times the `label` appears as 
//    [anchor](http://en.wikipedia.org/wiki/HTML_anchor#Anchor) 
//    text for a link to `title` on Wikipedia
// * `senseDocCount` is the number of documents in which the `label` appears as 
//    [anchor](http://en.wikipedia.org/wiki/HTML_anchor#Anchor) 
//    text for a link to `title` on Wikipedia

// From these counts we compute the three heuristic measures that estimate the 
// likelihood of a link being correct for the `label`. Note that we can have
// more than one `title` using the same `label`. The three heuristics are:
//
// * `linkProbability` is computed by dividing the `linkDocCount` by `docCount` 
//    and thus equals the percentage of documents in which the `label` appears as 
//    [anchor](http://en.wikipedia.org/wiki/HTML_anchor#Anchor) 
//    text for any link on Wikipedia.
// * `priorProbability` is computed by dividing `senseDocCount` by `linkDocCount` 
//    and thus equals the percentage of documents  where `title` is the target when 
//    `label` appears as [anchor](http://en.wikipedia.org/wiki/HTML_anchor#Anchor) 
//    text on Wikipedia.
// * `senseProbability` is the product of `linkProbability` and `priorProbability`
//    and thus equals the percentage of documents where `label` is a used as 
//    [anchor](http://en.wikipedia.org/wiki/HTML_anchor#Anchor) text to link 
//    to `target` out of all pages where `label` appears on Wikipedia.
//
// More generally, you can regard `linkProbability` as a measure of how likely
// `label` is to be a link, `priorProbability` as a measure of how disambiguous `label`
// is and `senseProbability` as a measure combining both characteristics.

// ***
// ### Translations
// 
// Wikipedia appears in many languages, so we list links to translations as well:
// 
// > http://semanticize.uva.nl/api/nl?text=UvA&pretty&translations
{
    "text": "UvA", 
    "status": "OK",
    "links": [
        {
            "id": 14815,
            "text": "UvA", 
            "label": "UvA", 
            "title": "Universiteit van Amsterdam", 
            "url": "http://nl.wikipedia.org/wiki/Universiteit%20van%20Amsterdam", 
            "linkProbability": 0.2946058091286307, 
            "priorProbability": 1.0, 
            "senseProbability": 0.2946058091286307, 
            "translations": {
                "fr": {
                    "url": "http://fr.wikipedia.org/wiki/Universit%C3%A9%20d%27Amsterdam", 
                    "title": "Universit\u00e9 d'Amsterdam"
                }, 
                "en": {
                    "url": "http://en.wikipedia.org/wiki/University%20of%20Amsterdam", 
                    "title": "University of Amsterdam"
                }, 
                "nl": {
                    "url": "http://nl.wikipedia.org/wiki/Universiteit%20van%20Amsterdam", 
                    "title": "Universiteit van Amsterdam"
                }, 
                "es": {
                    "url": "http://es.wikipedia.org/wiki/Universidad%20de%20%C3%81msterdam", 
                    "title": "Universidad de \u00c1msterdam"
                }
            }
        }
    ]
}

// *** 
// ### Images
//
// We obtain a representative image for a Wikipedia page, by scanning the article
// for the first image that is larger than 36 pixels in any dimension. 
// > http://semanticize.uva.nl/api/nl?text=UvA&pretty&image

{
    "text": "UvA", 
    "status": "OK",
    "links": [
        {
            "id": 14815,
            "text": "UvA", 
            "label": "UvA", 
            "title": "Universiteit van Amsterdam", 
            "url": "http://nl.wikipedia.org/wiki/Universiteit%20van%20Amsterdam", 
            "linkProbability": 0.2946058091286307, 
            "priorProbability": 1.0, 
            "senseProbability": 0.2946058091286307,
            "image_url": "http://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Agnietenkapel_%28Amsterdam%29.jpg/220px-Agnietenkapel_%28Amsterdam%29.jpg"
        }
    ]
}
// <img src="http://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Agnietenkapel_%28Amsterdam%29.jpg/220px-Agnietenkapel_%28Amsterdam%29.jpg" alt="UvA" height="80" style="float:right;" />
// For the UvA query the `image_url` to picture of the Agnietenkapel shown on the 
// right is returned. 
// Note that is not always possible to find a representative image. In that case, 
// no `image_url` will be included in the output.
//
// ***
// ### Normalization
// 
// The input string is normalized before semantic linking is performed. The same
// normalization is applied on the input string as well as on the anchor text in
// Wikipedia. Currently, three normalization methods are implemented:
// 
// * `dash` will replace all dashes (-) with a space, making 'Déjà-vu-feeling' the 
//   same as 'Déjà vu feeling'.
// * `accents` will remove accents from characters and convert the string to
//   [normal form KD (NFKD)](http://www.unicode.org/reports/tr44/tr44-4.html). 
//   This will yield in 'Déjà vu' being equal to 'Deja vu' after normalization.
// * `lower` will lowercase all text, making 'Déjà vu' the same as 'déjà_vu'.
//
// By default `dash` and `accents` are applied, but different combinations can
// be used:
// > http://semanticize.uva.nl/api/nl?text=UvA&pretty&normalize=lower,dash,accents
{
    "text": "UvA", 
    "status": "OK",
    "links": [
        {
            "text": "UvA", 
            "linkProbability": 0.14285714285714285, 
            "id": 94094, 
            "senseProbability": 0.0, 
            "title": "Uva", 
            "url": "http://nl.wikipedia.org/wiki/Uva", 
            "label": "UVA", 
            "priorProbability": 0.0
        }, 
        {
            "text": "UvA", 
            "linkProbability": 0.14285714285714285, 
            "id": 14815, 
            "senseProbability": 0.14285714285714285, 
            "title": "Universiteit van Amsterdam", 
            "url": "http://nl.wikipedia.org/wiki/Universiteit%20van%20Amsterdam", 
            "label": "UVA", 
            "priorProbability": 1.0
        }, 
        {
            "text": "UvA", 
            "linkProbability": 0.0, 
            "id": 94094, 
            "senseProbability": 0.0, 
            "title": "Uva", 
            "url": "http://nl.wikipedia.org/wiki/Uva", 
            "label": "UVa", 
            "priorProbability": 0
        }, 
        {
            "text": "UvA", 
            "linkProbability": 0.2946058091286307, 
            "id": 14815, 
            "senseProbability": 0.2946058091286307, 
            "title": "Universiteit van Amsterdam", 
            "url": "http://nl.wikipedia.org/wiki/Universiteit%20van%20Amsterdam", 
            "label": "UvA", 
            "priorProbability": 1.0
        }, 
        {
            "text": "UvA", 
            "linkProbability": 0.25, 
            "id": 1237144, 
            "senseProbability": 0.03571428571428571, 
            "title": "Uva (Vimioso)", 
            "url": "http://nl.wikipedia.org/wiki/Uva%20%28Vimioso%29", 
            "label": "Uva", 
            "priorProbability": 0.14285714285714285
        }, 
        {
            "text": "UvA", 
            "linkProbability": 0.25, 
            "id": 958058, 
            "senseProbability": 0.21428571428571427, 
            "title": "Uva (Sri Lanka)", 
            "url": "http://nl.wikipedia.org/wiki/Uva%20%28Sri%20Lanka%29", 
            "label": "Uva", 
            "priorProbability": 0.8571428571428571
        }, 
        {
            "text": "UvA", 
            "linkProbability": 0.25, 
            "id": 94094, 
            "senseProbability": 0.0, 
            "title": "Uva", 
            "url": "http://nl.wikipedia.org/wiki/Uva", 
            "label": "Uva", 
            "priorProbability": 0.0
        }
    ]
}

// ***
// ### Filters
// 
// Our retrieval model for semantic linking is recall oriented. This means that
// we produce very many link candidates, even if they are not very relevant. In fact,
// if a label is used as anchor text on Wikipedia just once it is considered a link
// candidate if the label occurs in the input string.
// 
// This makes it clear that it is important to rank and filter the link candidates 
// that are produced. For these the earlier mentioned heuristic measures can be used.
// In our experience, `senseProbability` is best suited for this. A value of at least
// 0.3 produces sensible results. Furthermore, making sure that a label is used as
// a link in at least a minimal number of documents (say 5 times).
//
// You can apply a filter for this:
// >  http://semanticize.uva.nl/api/nl?text=Karel%20de%20Grote&pretty&filter=senseProbability%3E0.3,linkDocCount%3E=5&counts
{
    "text": "Karel de Grote", 
    "status": "OK",
    "links": [
        {
            "id": 5337, 
            "text": "Karel de Grote", 
            "label": "Karel de Grote", 
            "title": "Karel de Grote", 
            "url": "http://nl.wikipedia.org/wiki/Karel%20de%20Grote", 
            "linkProbability": 0.8417582417582418, 
            "priorProbability": 0.9989094874591058, 
            "senseProbability": 0.8417582417582418, 
            "docCount": 910
            "occCount": 1441, 
            "linkDocCount": 766, 
            "linkOccCount": 917, 
            "senseOccCount": 916, 
            "senseDocCount": 766, 
        }
    ]
}

// *** 
// ### Context
//
// You can specify a context, in which you can filter links to make sure they are unique.
// >  http://semanticize.uva.nl/api/nl?context=test&filter=unique&text=UvA
{
    "text": "UvA",
    "status": "OK",
    "links": [
        {
            "id": 14815,
            "text": "UvA", 
            "label": "UvA", 
            "title": "Universiteit van Amsterdam", 
            "url": "http://nl.wikipedia.org/wiki/Universiteit%20van%20Amsterdam", 
            "linkProbability": 0.2946058091286307, 
            "priorProbability": 1.0, 
            "senseProbability": 0.2946058091286307 
        }
    ]
}
// Doing the same request again will result in no links:
// >  http://semanticize.uva.nl/api/nl?context=test&filter=unique&text=UvA
{
    "text": "UvA", 
    "status": "OK",
    "links": []
}

// *** 
// ### Machine Learning Models
//
// The webservice can also be used for computing features and applying machine 
// learning models that are trained in specific settings. This part is 
// still undergoing heavy development. Therefore, computing these features and 
// applying models are currently not publicly available. If you are interested in 
// this, contact [Daan](http://staff.science.uva.nl/~dodijk/).
