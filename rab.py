import roles

def create_url(values, gemeente='', startrecord = 0):
    vrij_tekst = values['vrij_tekst']
    vrij_periode = values['vrij_periode']
    vrij_plaats = values['vrij_plaats']
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

    zoekwijze = 's' if values['matchtype'] == 'Exact' else 'p'

    if vrij_tekst != '':
        vrij_tekst = 'text='+ vrij_tekst + '&'
    if vrij_periode != '':
        vrij_periode = 'periode='+ vrij_periode + '&'
    if vrij_plaats != '':
        vrij_plaats = 'plaatsnaam='+ vrij_plaats + '&'


    if startrecord:
        start = 'start/' + str(startrecord)
    else :
        start = ''

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
    + "q/zoekwijze/"+zoekwijze + "/" + beroep1 + start + "?"+vrij_tekst + vrij_periode + vrij_plaats + "M=" + zw_m + "&V=" + zw_v + "&O=" + zw_o + "&persoon_0_periode_geen=0&sort=akte_datum&direction=asc" \
    + gemeente + periode
    #url = "https://search.arch.be/nl/zoeken-naar-personen/zoekresultaat/" + an1 + vn1 + rol1 + an2 + vn2 + rol2 + "?&sort=akte_datum&direction=asc" + gemeente
    return url