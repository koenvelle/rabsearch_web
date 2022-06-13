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
import folium

app = Flask(__name__)
progress = 0

def create_url(values, gemeente):
    vn1 = values['pers1_voornaam']
    an1 = values['pers1_achternaam']
    vn2 = values['pers2_voornaam']
    an2 = values['pers2_achternaam']
    beroep1 = values['pers1_beroep']
    rol1 = values['pers1_rol']
    rol2 = values['pers2_rol']
    periode = values['akteperiode']
    zw_m = '1' if 'zw_m' in values.keys() and values['zw_m'] == '1' else '0'
    zw_v = '1' if 'zw_v' in values.keys() and values['zw_v'] == '1' else '0'
    zw_o = '1' if 'zw_o' in values.keys() and values['zw_o'] == '1' else '0'

    print(periode, file=sys.stderr)

    zoekwijze = 's' if values['matchtype'] == 'Exact' else 'p'

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
    if periode != '':
        periode = "&akteperiode=" + periode

    url = "https://search.arch.be/nl/zoeken-naar-personen/zoekresultaat/" + an1 + vn1 + rol1 + an2 + vn2 \
    + rol2 \
    + "q/zoekwijze/"+zoekwijze + "/" + beroep1 + "?M=" + zw_m + "&V=" + zw_v + "&O=" + zw_o + "&persoon_0_periode_geen=0&sort=akte_datum&direction=asc" \
    + gemeente + periode
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
        self.__hitmap_locations = []
        self.__match_indexes = match_indexes
        self.__progress = 0

        threading.Thread.__init__(self)

    def generate_hit_map(self):
        radius = self.__values['radius']
        x, centre = get_city_location(self.__gemeentes[0])
        m = folium.Map(location=centre, zoom_start=10, height=550)
        #circle = folium.Circle(location=centre, radius=radius * 1000)
        #circle.add_to(m)


        if len(self.__gemeentes):

            for location in self.__hitmap_locations:
                marker = folium.Marker(
                    [location[1], location[2]],
                    popup="<a href=" + location[4] + "> Aantal hits: " + location[3] + "</a>",
                    tooltip=location[0] + " hits: " + location[3]
                )
                marker.add_to(m)
        return m._repr_html_()

    def collect_results(self):

        self.__progress = 0
        for item in (self.__gemeentes):
            url = create_url(self.__values, item)

            if self.__stop_requested is False:
                # Don't overload server....
                time.sleep(.5)
                print("  worker requests url " + url, file=sys.stderr)
                r = requests.get(url)
                print("  worker returned ", file=sys.stderr)

                lines = str(r.content).split('\n')
                pattern = re.compile(".*Resultaten\s(\d+\s)-\s(\d+\s)van\s(\d+\s).*")

                for line in lines:
                    match = pattern.match(line)
                    if match is not None:
                        hit_count = match.groups()[2]
                        self.__results.append(item + ' (aantal : ' + hit_count + ')')
                        self.__urls.append(url)
                        name, (lat, lon) = get_city_location(item)
                        self.__hitmap_locations.append([name, lat, lon, hit_count, url])

                self.__progress = self.__progress + 1

        print("  worker done ", file=sys.stderr)

        self.__stop_requested = False

    def run(self):
        self.__done = False
        self.collect_results()
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
        return int((self.__progress * 100) / len(self.__gemeentes))

    def stop(self):
        self.__stop_requested = True

    def show_all(self, val=True):
        self.__show_all= val

rws  = dict()

@app.route("/get_map", methods=['GET'])
def get_map():
    rw_id = int(request.args["workerid"])
    print("Requesting map for workerid " + str(rw_id), file=sys.stderr)

    if rw_id not in rws.keys():
        print("  worker id " + str(rw_id) + " not in store "+ str(rws.keys()) +", returning -1", file=sys.stderr)
    elif rws[rw_id].completion() == 100:
        print("  worker complete", file=sys.stderr)
        map = rws[rw_id].generate_hit_map()
        print(map, file=sys.stderr)
        return map
    else :
        map = rws[rw_id].generate_hit_map()
        return map
    return


@app.route("/get_progress", methods=['GET'])
def get_progress():
    rw_id = int(request.args["workerid"])
    print("Requesting progress for workerid " + str(rw_id), file=sys.stderr)

    if rw_id not in rws.keys():
        print("  worker id " + str(rw_id) + " not in store "+ str(rws.keys()) +", returning -1", file=sys.stderr)
        retval = -1
        retresults = []
        returls = []
    elif rws[rw_id].completion() == 100:
        print("  worker complete", file=sys.stderr)
        retresults = rws[rw_id].results()
        returls = rws[rw_id].urls()
        retval = -1
    else :
        retresults = rws[rw_id].results()
        returls = rws[rw_id].urls()
        retval = rws[rw_id].completion()
        print("  worker at " + str(retval), file=sys.stderr)

    return json.dumps( {'progress':retval, 'results': retresults , 'urls' : returls} )

@app.route("/zoek_regio", methods=['POST'])
def zoek_regio():
    global rws
    r = requests.get("http://www.koenvelle.be/rabsearch/zoek_regio")
    print(r, file=sys.stderr)
    print(request.args, file=sys.stderr)
    aktegemeente = request.form['aktegemeente']
    radius = int(request.form['radius'])

    # find all locations around 'aktegemeente'
    search_locations = get_places_in_radius(aktegemeente, radius)

    match_indexes = []
    new_rw = ResultsWorker(request.form, search_locations, match_indexes)
    rw_id = len(rws) + 1
    rws[rw_id] = new_rw
    new_rw.show_all(False)
    new_rw.start()
    print("zoek_regio_return", file=sys.stderr)
    return str(rw_id)

@app.route("/")
def index():
    r = requests.get("http://www.koenvelle.be/rabsearch/visit")
    print(r, file=sys.stderr)
    resultaten = [];
    return render_template("index.html",gemeentes=city_names, rollen=person_roles, resultaten=resultaten)

if __name__ == '__main__':
    app.run(threaded=False, processes=3)

