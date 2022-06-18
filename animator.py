from rab import create_url
import requests
import citylocs
import folium
import os
import time
from pathlib import Path

from selenium import webdriver
from html.parser import HTMLParser
import imageio



def get_all_baptisms(name):
    values = {
        'pers1_voornaam':'',
        'pers1_achternaam':name,
        'pers2_voornaam': '',
        'pers2_achternaam': '',
        'pers1_beroep':'',
        'pers1_rol':'Dopeling',
        'pers2_rol': '',
        'akteperiode': '',
        'zw_m' : '0',
        'zw_v' : '0',
        'zw_o' : '0',
        'matchtype': 'Exact'
    }

    url = create_url(values)
    print(url)
    r = requests.get(url)

    results = []
    startrecord = 0

    parser = PersonResultsParser(results)
    while startrecord is not None:
        url = create_url(values, startrecord=startrecord)
        print(url)
        r = requests.get(url)
        parser = PersonResultsParser(results)
        parser.feed(r.text)
        startrecord = parser.next_record()

    print(len(results))
    return results

def bucketize_by_decade(entries):
    #['BOVEKERKE', (51.0542624, 2.9634051), '16-10-1799', 'Coleta Sophia']
    buckets = {}
    buckets[0] = []
    for e in entries:
        if e[2] != '' and e[2] is not None:
            y = 0
            if '-' in e[2]:
                d = str(e[2])
                y = d.split('-')[2]
            elif '/' in e[2]:
                y = e[2].split('/')
                y = y[-1]
            else:
                y = e[2]
            decade = round(int(y) / 10 - .5)
            if decade not in buckets.keys():
                buckets[decade] = []
            buckets[decade].append(e)
        else:
            buckets[0].append(e)
    return buckets

def create_animation(decade_buckets, create_gif = False):
    maps = []
    centre = (51.011310050000006, 4.192796388661321)

    for dec, entries in decade_buckets.items():
        m = folium.Map(location=centre, zoom_start=9)
        m.png_enabled
        for e in entries:
            location = e[1]
            marker = folium.Marker(location,
                popup="",
                tooltip=""
            )
            marker.add_to(m)
        fname = str(dec)
        title_html = '''
                     <h3 align="left" style="font-size:22px"><b>{}</b></h3>
                     '''.format('Decade: ' + str(dec*10))
        m.get_root().html.add_child(folium.Element(title_html))
        maps.append((dec, m._repr_html_()))
        if create_gif:
            m.save(fname+".html")
            tmpurl = 'file://{path}/{mapfile}.html'.format(path=os.getcwd(), mapfile=fname)

            browser = webdriver.Chrome()
            browser.maximize_window()
            browser.get(tmpurl)

            # Give the map tiles some time to load
            time.sleep(2)
            browser.save_screenshot(fname + '.png')
            browser.quit()
            os.remove(fname+".html")

    if create_gif:
        image_path = Path()

        images = list(image_path.glob('*.png'))
        image_list = []
        for file_name in images:
            image_list.append(imageio.imread(file_name))
            os.remove(file_name)

        imageio.mimwrite('GifMap.gif', image_list, fps=2)
    return maps

def geolocate(entries):
    r=[]
    notfound=[]
    for e in entries:
        (name, location) = citylocs.get_city_location(e[1].upper())
        l = ''
        if location != (0,0):
            l = [name, location, e[2],e[4]]
            r.append(l)
        else:
            notfound.append(l)
    return r, notfound

class PersonDetailsParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.expect_data = False
        self.year = None
    def handle_starttag(self, tag, attrs):
        if tag == 'td':
            self.expect_data = True
        return
    def handle_endtag(self, tag):
        if tag == 'td':
            self.expect_data = False
        return
    def handle_data(self, data):
        if self.expect_data:
            data = data.strip()
            if data.startswith('(') and data.endswith(')'):
                self.year = data.strip('()')
        return


class PersonResultsParser(HTMLParser):
    def __init__(self, results):
        HTMLParser.__init__(self)
        self.__inbody = False;
        self.__currentrow = []
        self.__addrowdata = False;
        self.__rowdata = ''
        self.__expectcounterdata = False
        self.__results = results
        self.__recordtotal = 0
        self.__recordfinal = False

    def handle_starttag(self, tag, attrs):
        self.__expectcounterdata = False
        if tag == 'div' and attrs == [('class', 'resultscounter')]:
            self.__expectcounterdata = True
        if tag == 'tbody':
            self.__inbody = True
        if tag == 'tr'  and self.__inbody:
            self.__inrow= True
            self.__currentrow = []
        if tag == 'td' and self.__inbody :
            self.__rowdata = ''
            if len(attrs) == 0:
                self.__addrowdata = True
            elif attrs == [('class', 'nowrap')]:
                self.__addrowdata = True
        if tag == 'a' and self.__inbody:
            appendhref = False
            for key, value in attrs:
                if (key, value) == ('class', 'modal'):
                    appendhref = True
                if appendhref and key == 'href':
                    self.__currentrow.append(value)
                    appendhref = False;

    def handle_endtag(self, tag):
        if tag == 'div':
            self.__expectcounterdata = False
        if tag == 'tbody':
            self.__inbody = False
        if tag == 'tr' and self.__inbody:
            if self.__currentrow[2] == '':
                url = "https://search.arch.be/" + self.__currentrow[6]
                print(url)
                r = requests.get(url)
                p = PersonDetailsParser()
                p.feed(r.text)
                self.__currentrow[2] = p.year

            self.__results.append(self.__currentrow)
            self.__inrow = False
        if tag == 'td' and self.__inbody:
            self.__addrowdata = False
            self.__currentrow.append(self.__rowdata)
        return

    def handle_data(self, data):
        if self.__expectcounterdata is True:
            data = data.split()
            self.__recordtotal =  data[5]
            self.__recordend = data[3]
            self.__recordfinal = (data[3] == self.__recordtotal)
        if self.__addrowdata:
            self.__rowdata = data

    def next_record(self):
        if self.__recordfinal :
            return None
        return self.__recordend

results = get_all_baptisms('Dossche')
print(results[1])

geolocated, notfound = geolocate(results)

print('entries without location :'+ str(len(notfound)))
print(geolocated)
decade_buckets = bucketize_by_decade(geolocated)
print('entries without date :'+ str(len(decade_buckets[0])))
create_animation(decade_buckets, create_gif=True)

