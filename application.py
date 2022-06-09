from flask import Flask, render_template
from citylocs import *

from roles import person_roles
import roles
from flask import request
import json
import sys
import requests
import re
import threading
from geopy import distance
import time

#host on heroku

app = Flask(__name__)

votes = 0

gemeentes={'Gistel', 'Brugge', 'Erps-Kwerps'}
resultaten = [('koekelare','1.html'), ('oostende', '2')]
progress = 0 


def create_url(values, gemeente):
    vn1 = values['pers1_voornaam']
    an1 = values['pers1_achternaam']
    vn2 = values['pers2_voornaam']
    an2 = values['pers2_achternaam']
    beroep1 = values['pers1_beroep']
    rol1 = values['pers1_rol']
    rol2 = values['pers2_rol']
    #periode = values['akteperiode']
    zw_m = '1' if 'zw_m' in values.keys() and values['zw_m'] == '1' else '0'
    zw_v = '1' if 'zw_v' in values.keys() and values['zw_v'] == '1' else '0'
    zw_o = '1' if 'zw_o' in values.keys() and values['zw_o'] == '1' else '0'

    zoekwijze = 's' if values['matchtype'] == 'Exact' else 'p'
    zoekwijze = 's'

    if vn1 != '':
        vn1 = "q/persoon_voornaam_t_0/" + vn1 + '/'
    if an1 != '':
        an1 = "q/persoon_achternaam_t_0/" + an1 + '/'
    if beroep1 != '':
        beroep1 = "q/persoon_beroep_s_0/" + beroep1 + "/"
    if vn2 != '':
        vn2 = "q/persoon_voornaam_t_1/" + vn2 + '/'
    if an2 != '':
        an2 = "q/persoon_achternaam_t_1/" + an2 + '/'
    if rol1 != '':
        rol1 = str([id for (id, type) in roles.person_roles if type == rol1][0])
        rol1 = "q/persoon_rol_s_0/" + rol1 + '/'
    if rol2 != '':
        rol2 = str([id for (id, type) in roles.person_roles if type == rol2][0])
        rol2 = "q/persoon_rol_s_1/" + rol2 + '/'
    if gemeente != '':
        gemeente = "&aktegemeente=" + gemeente
    if '(' in gemeente:
        gemeente = gemeente.split('(')[0]
    #if periode != '':
    #    periode = "&akteperiode=" + periode

    url = "https://search.arch.be/nl/zoeken-naar-personen/zoekresultaat/" + an1 + vn1 + rol1 + an2 + vn2 \
	+ rol2 \
	+ "q/zoekwijze/"+zoekwijze + "/" + beroep1 + "?M=" + zw_m + "&V=" + zw_v + "&O=" + zw_o + "&persoon_0_periode_geen=0&sort=akte_datum&direction=asc" \
	+ gemeente 
	#+ periode
    #url = "https://search.arch.be/nl/zoeken-naar-personen/zoekresultaat/" + an1 + vn1 + rol1 + an2 + vn2 + rol2 + "?&sort=akte_datum&direction=asc" + gemeente
    return url
	
def get_places_in_radius(src, radius):
    matches = []
    if src != '' and (src in city_names):
        naam, (src_latitude, src_longitude) = get_city_location(src)

        distances = []

        for dest, (dest_latitude, dest_longitude) in citylocs:
            d = distance.distance((src_latitude, src_longitude), (dest_latitude, dest_longitude))
            distances.append((round(d.km, 2), dest))

        distances.sort()

        for d in distances:
            if d[0] <= radius:
                matches.append(d[1])

    return matches
	
class ResultsWorker(threading.Thread):

    def __init__(self, values, gemeentes, match_indexes):
        self.__done = False
        self.__stop_requested = False
        self.__show_all = True
        self.__gemeentes = gemeentes
        self.__values = values
        self.__results = []
        self.__urls = []
        self.__match_indexes = match_indexes
		
        threading.Thread.__init__(self)

    def collect_results(self, values, gemeentes, results, match_indexes):
	
        self._progress = 0
        hit_map_locations = []
        for item in (gemeentes):
            url = create_url(values, item)

            if self.__stop_requested is False:
                # Don't overload server....
                time.sleep(.5)
                r = requests.get(url)

                lines = str(r.content).split('\n')
                pattern = re.compile(".*Resultaten\s(\d+\s)-\s(\d+\s)van\s(\d+\s).*")

                for line in lines:
                    match = pattern.match(line)
                    if match is not None:
                        hit_count = match.groups()[2]
                        results.append(item + ' (aantal : ' + hit_count + ')')
                        self.__urls.append(url)
                        match_indexes.append(len(results) -1)
                        #name, (lat, lon) = get_city_location(item)
                        #hit_map_locations.append([name, lat, lon, hit_count, url])
                        #update_radius_results(results)

                self._progress = self._progress + 1

        self.__stop_requested = False

    def run(self):
        self.__done = False
        self.collect_results(self.__values, self.__gemeentes, self.__results, self.__match_indexes)
        self.__done = True
        sys.exit()

    def done(self):
        return self.__done

    def clear(self):
        self.__done = False
        self.__stop_requested = False
		
    def results(self):
        return self.__results
		
    def urls(self):
        return self.__urls

	

    def completion(self):
        return int((self._progress * 100) / len(self.__gemeentes))

    def stop(self):
        self.__stop_requested = True

    def show_all(self, val=True):
        self.__show_all= val
		
rw  = None

@app.route("/get_progress", methods=['POST'])
def get_progress():	
	retval = 0
	if rw is None :
		print("get progress", file=sys.stderr)
		retval = -1
	elif rw.completion() == 100:
		retval = -1
	else :
		retval = rw.completion()
		
	return json.dumps( {'progress':retval, 'results': rw.results(), 'urls' : rw.urls() } )
	

@app.route("/zoek_regio", methods=['POST'])
def zoek_regio():
	global rw
	progress = 0
	print(request.form, file=sys.stderr)
	aktegemeente = request.form['aktegemeente']
	radius = int(request.form['radius'])
	
	# find all locations around 'aktegemeente'
	search_locations = get_places_in_radius(aktegemeente, radius)
	
	match_indexes = []
	rw  = ResultsWorker(request.form, search_locations, match_indexes)
	rw.show_all(False)
	rw.start()
	
	return render_template("index.html", votes=votes, gemeentes=city_names, rollen=person_roles, resultaten=resultaten)

@app.route("/")
def index():

    global resultaten
    resultaten = [];
    return render_template("index.html", votes=votes, gemeentes=city_names, rollen=person_roles, resultaten=resultaten)
	
if __name__ == '__main__':
    app.run(threaded=False, processes=3)

