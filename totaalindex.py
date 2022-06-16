import requests
from html.parser import HTMLParser

import citylocs

url = "https://dataindexen.familiekunde-vlaanderen.be/SearchKlappers/showDetailResults.php"

table_names = ["001_AALST",
    "002_ANTWERPEN",
    "003_BRUGGE",
    "004_BRUSSEL",
    "005_DENDERMONDE",
    "006_DIKSMUIDE",
    "007_EEKLO",
    "008_GENT",
    "009_HALLE_VILVOORDE",
    "010_HASSELT",
    "011_IEPER",
    "012_KORTRIJK",
    "013_LEUVEN",
    "014_MAASEIK",
    "015_MECHELEN",
    "016_OOSTENDE",
    "017_OUDENAARDE",
    "018_ROESELARE",
    "019_SINT_NIKLAAS",
    "020_TIELT",
    "021_TONGEREN",
    "022_TURNHOUT",
    "023_VEURNE",
]


class DetailResultsParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.__expect_data = False
        self.__expect_results = False
        self.__rowdata = []
        self.results = []

    def handle_starttag(self, tag, attrs):
        #print("Encountered a start tag:", tag)
        if tag == 'tr':
             self.__rowdata= []

        if tag == 'td':
            self.__expect_data = True

    def handle_endtag(self, tag):
        #print("Encountered an end tag :", tag)
        if tag == 'table':
            self.__expect_results = False
        if tag == 'tr':
            if self.__expect_results:
                self.results.append(self.__rowdata)
            if self.__rowdata[0] == 'Familienaam':
                self.__expect_results = True

        return

    def handle_data(self, data):
        #print("Encountered some data  :", data)
        if self.__expect_data:
            self.__rowdata.append(data)
            self.__expect_data = False


def annotate_with_locations(results):
    annotated_results = []
    for (table, locations) in results:
        annotated_locations = []
        for location in locations:
            #print("locating" + str(location[1].upper()))
            if str(location[1].upper()) in citylocs.city_names:
                annotated_location = citylocs.get_city_location(str(location[1]).upper())
                entry = [annotated_location[0], annotated_location[1], location[2]]
                annotated_locations.append([annotated_location[0], annotated_location[1], location[2]])
            else :
                print("no match for " + str(location[1].upper()))
        annotated_results.append((table,annotated_locations))
    return annotated_results

def get_totaal_index(name:str):
    results = []
    myobj= {'active_group': 'ttind', 'active_table': '', 'active_db': 'ind_ttind', 'sort': 'no_sort',
            'operator_family_name': 'is gelijk aan', 'field_family_name': name}

    for table in table_names :
        myobj['active_table'] = table

        x = requests.post(url, data=myobj)
        parser = DetailResultsParser()
        parser.feed(x.text)

        if len(parser.results):
            results.append((table, parser.results))
    return results