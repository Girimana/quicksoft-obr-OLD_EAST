from django.http import HttpResponseRedirect
from .models import Stock
import json
import requests
from requests.structures import CaseInsensitiveDict
from django.db.models import Q

# ---------------------------------------
class Object:
    """
    Dynamic object for (Stock and Items)
    """

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

# ---------------------------------------
class AuthenticationEBMS:
    """
    EBMS authentication
    """
    _token = None
    _connected = False
    _password = False
    _msg = ""

    def __init__(self, username, password, url):
        self.username = username
        self._password = password
        self.url = url

    def connect(self):
        response = requests.post(
            self.url,
            data=json.dumps(
                {
                    "username": self.username,
                    "password": self._password
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        if (response.status_code == 200):
            self._token = response.json()['result']['token']
            self._connected = True
        else:
            self._token = None
            self._connected = False
            x = json.loads(response.text)
            self._msg = x['msg']

        return self._connected

    @property
    def token(self):
        return self._token

    @property
    def is_connected(self):
        return self._connected

# ---------------------------------------
def LoadAndSaveStockFromStringList(lst):
    """
    Load invoice and details from string list (MSSQL)
    """
    if not lst:
        return None, None

    # Load invoice data from first list
    obj_str_invoice = lst[0].stock.split(';')  # MSSQL.table.facture culumn
    obj_str_num = lst[0].reference

    invoice = Object()
    invoice.system_or_device_id = obj_str_invoice[0].strip()
    invoice.item_code = obj_str_invoice[1].strip()
    invoice.item_designation = obj_str_invoice[2].strip()
    invoice.item_quantity = obj_str_invoice[3].strip()
    invoice.item_measurement_unit = obj_str_invoice[4].strip()
    invoice.item_purchase_or_sale_price = obj_str_invoice[5].strip()
    invoice.item_purchase_or_sale_currency = obj_str_invoice[6].strip()
    invoice.item_movement_type = obj_str_invoice[7].strip()
    invoice.item_movement_invoice_ref = obj_str_invoice[8].strip()
    invoice.item_movement_description = obj_str_invoice[9].strip()
    invoice.item_movement_date = obj_str_invoice[10].strip()

    # Convert invoice obect into json format
    invoice_json = json.loads(invoice.toJSON())

    # Save Invoices/Details to json file
    with open("settings.json", 'r') as file:
        settings = json.load(file)
        jsonFile = open('{}{}.json'.format(
            settings['stock_directory'], obj_str_num.replace("/", "_")), "w")
        jsonFile.write(json.dumps(invoice_json))
        jsonFile.close()

    return invoice

# ---------------------------------------
def load_stock_json_file_by_reference(reference):
    """
    Load invoice from json file by reference (referece is the name of object)
    """
    invoice = None
    
    with open("settings.json", 'r') as file:
        settings = json.load(file)
        with open('{}{}.json'.format(settings['stock_directory'], reference), 'r') as file:
            invoice = json.load(file)

    return invoice


# ---------------------------------------
def send_stock(request):
    # send stock movement
    url_next = request.GET['url_next'] + '&paramId=' + request.GET['paramId']

    reference = request.GET['reference']

    auth = None
    invoice = None

    try:
        lst = Stock.objects.filter(reference=reference)
        invoice = LoadAndSaveStockFromStringList(lst)
    except:
        try:
            invoice = load_stock_json_file_by_reference(reference)
        except:
            print("Error, fichier json not created")
            pass
    try:
        # load json file by company
        
    
        with open("settings.json", 'r') as file:
            settings = json.load(file)
            if settings:
                auth = AuthenticationEBMS(
                    settings['username'], settings['password'], settings['url_api_login'])
                auth.connect()  # Connect to endpoint
    except:
        # Mettre à jour la colonne envoyee et response de la table 'Stock'
        if (auth._msg == "Nom d’utilisateur ou mot de passe incorrect."):
            obj = Stock.objects.filter(reference=reference)
            for stocks in obj:
                stocks.envoyee = False
                stocks.response = auth._msg
                stocks.save()

    if auth.is_connected and invoice:
        try:
            # Load json invoice in '/temps'
            with open('{}{}.json'.format(settings['stock_directory'], reference.replace("/", "_")), 'r') as json_file_invoice:
                invoice_to_send = json.load(json_file_invoice)

            # Send invoice (add invoice)
            url = settings['url_api_add_stock_mouvement']
            headers = CaseInsensitiveDict()
            headers["Accept"] = "application/json"
            headers["Authorization"] = "Bearer {}".format(auth.token)
            response = requests.post(
                url,
                data=json.dumps(invoice_to_send),
                headers=headers
            )
            if (response.status_code in [200, 201, 202]):
                # Mettre à jour la colonne envoyee de la table 'Stock'
                obj = Stock.objects.filter(reference=reference)
                if obj:
                    for x in obj:
                        x.envoyee = True
                        msg = json.loads(response.text)
                        x.response = msg['msg']
                        x.save()
                    
                url_next += "&msg=" + \
                    "====> Transaction Réf° {} envoyée avec succès à l'OBR".format(
                        reference)

                print("====> La transaction de Réf° {} a été ajoutée avec succès à l'OBR!".format(
                    reference))
            else:
                # Mettre à jour la colonne envoyee de la table 'Stock'
                obj = Stock.objects.filter(reference=reference)
                if obj:
                    for x in obj:
                        x.envoyee = False
                        msg = json.loads(response.text)
                        x.response = msg['msg']
                        x.save()
                try:
                    msg = json.loads(response.text)
                    msg = ", message: " + msg['msg']
                except:
                    try:
                        msg = json.loads(response.text)
                        msg = ", message: " + msg['msg']
                    except Exception as e:
                        msg = ", message: " + str(e)

                url_next += "&msg=" + \
                    "====> ERREUR, d'envoi de la facture Réf {} à l'OBR {}".format(
                    reference, msg)
                print("====> ERREUR, d'envoi du mouvement Réf {} à l'OBR {}".format(
                    reference, msg))

        except Exception as e:
            url_next += "&msg=" + \
                "====> ERREUR, d'envoi du mouvement Réf {} à l'OBR, message: {}".format(
                reference, str(e))
            print("====> ERREUR d'envoi du mouvement Réf {} à l'OBR, message: {}".format(
                reference, str(e)))
            # Mettre à jour la colonne envoyee de la table 'Stock'
            obj = Stock.objects.filter(reference=reference)
            if obj:
                for x in obj:
                    x.envoyee = False
                    x.response = "Problème survenue lors de l'envoie de la facture"
                    x.save()
    elif invoice is None:
        print("====> ERREUR, Erreur de création du fichier Json facture ou donnée incorrect générée par QuickSoft, Réf {}".format(reference))
        url_next += "&msg=" + \
            "====> ERREUR, Erreur de création du fichier Json facture ou donnée incorrect générée par QuickSoft, Réf {}".format(
                reference)
        # Mettre à jour la colonne envoyee de la table 'Invoice'
        obj = Stock.objects.filter(
            reference=reference)
        if obj:
            for x in obj:
                x.envoyee = False
                x.response = "Pas de facture, problème du côté de QuickSoft"
                x.save()
    elif not auth.is_connected or not auth.token:
        print("====> ERREUR d'authentification à l'API de l'OBR")
        # Mettre à jour la colonne envoyee de la table 'Stock'
        obj = Stock.objects.filter(reference=reference)
        if auth._msg:
            if obj:
                for x in obj:
                    url_next += "&msg=" + \
                        "====> ERREUR d'accès au serveur de l'OBR, {}".format(
                            auth._msg)
                    x.response = "ERREUR d'accès au serveur de l'OBR, {}".format(
                        auth._msg)
                    x.envoyee = False
                    x.save()
            
        else:
            if obj:
                for x in obj:
                    url_next += "&msg=" + "====> ERREUR de connexion à l'API de l'OBR"
                    x.response = "ERREUR de connexion à l'API de l'OBR"
                    x.envoyee = False
                    x.save()
    else:
        print("====> ERREUR innattendue pour l'envoi de la facture, facture Réf {}, veuillez contacter votre fournisseur de logiciel".format(reference))
        url_next += "&msg=" + \
            "====> ERREUR innattendue pour l'envoi de la facture, facture Réf {}, veuillez contacter votre fournisseur de logiciel".format(
                reference)

    return HttpResponseRedirect(url_next)

# ---------------------------------------
def send_stock_offline():
    """
    Send invoice via API
    """

    auth = None
    invoice = None

    x = Stock.objects.filter(Q(envoyee='False') | Q(envoyee__isnull=True))
    for invoice_notsend in x:
        

        try:
            lst = Stock.objects.filter(reference=invoice_notsend.reference)
            invoice = LoadAndSaveStockFromStringList(lst)
        except:
            try:
                invoice = load_stock_json_file_by_reference(
                    invoice_notsend)
            except:
                print("Error, fichier json not created")
                pass

        try:
            with open("settings.json", 'r') as file:
                settings = json.load(file)
                if settings:
                    auth = AuthenticationEBMS(
                        settings['username'], settings['password'], settings['url_api_login'])
                    auth.connect()  # Connect to endpoint
        except:
            if (auth._msg == "Nom d’utilisateur ou mot de passe incorrect."):
                # Mettre à jour la colonne envoyee de la table 'Stock'
                obj = Stock.objects.filter(
                    reference=invoice_notsend.reference)
                if obj:
                    for invoice_with_many_articles in obj:
                        invoice_with_many_articles.envoyee = False
                        invoice_with_many_articles.response = auth._msg
                        invoice_with_many_articles.save()
        
        if auth.is_connected and invoice:
            try:
                # Load json invoice in '/temps'
                with open('{}{}.json'.format(settings['stock_directory'], invoice_notsend.reference.replace("/", "_")), 'r') as json_file_invoice:
                    invoice_to_send = json.load(json_file_invoice)

                # Send invoice (add invoice)
                url = settings['url_api_add_stock_mouvement']
                headers = CaseInsensitiveDict()
                headers["Accept"] = "application/json"
                headers["Authorization"] = "Bearer {}".format(auth.token)
                response = requests.post(
                    url,
                    data=json.dumps(invoice_to_send),
                    headers=headers
                )
                if (response.status_code in [200, 201, 202]):
                    # Mettre à jour la colonne envoyee de la table 'Stock'
                    obj = Stock.objects.filter(
                        reference=invoice_notsend.reference)
                    if obj:
                        msg = json.loads(response.text)
                        msg = msg['msg']
                        for stock_data in obj:
                            if (stock_data.envoyee == False) or (stock_data.envoyee == None):
                                stock_data.envoyee = True
                                stock_data.response= msg
                                stock_data.save()

                    print("====> La transaction de Réf° {} a été ajoutée avec succès à l'OBR".format(
                        invoice_notsend.reference))
                else:
                    # Mettre à jour la colonne envoyee de la table 'Stock'
                    obj = Stock.objects.filter(
                        reference=invoice_notsend.reference)
                    if obj:
                        msg = json.loads(response.text)
                        msg = msg['msg']
                        for stock in obj:
                            stock.envoyee = False
                            stock.response = msg
                            stock.save()

                    try:
                        msg = json.loads(response.text)
                        msg = ", message: " + msg['msg']
                    except:
                        try:
                            msg = json.loads(response.content)
                            msg = ", message: " + msg['msg']
                        except Exception as e:
                            msg = ", message: " + str(e)

                    print("====> ERREUR, d'envoi du mouvement de Réf {} à l'OBR {}".format(
                        invoice_notsend.reference, msg))

            except Exception as e:
                # Mettre à jour la colonne envoyee de la table 'Stock'
                obj = Stock.objects.filter(
                    reference=invoice_notsend.reference)
                if obj:
                    for x in obj:
                        x.envoyee = False
                        x.response = "Problème survenue lors de l'envoie du mouvement"
                        x.save()

                print("====> ERREUR d'envoi du mouvement Réf {} à l'OBR, message: {}".format(
                    invoice_notsend.reference, str(e)))

        elif invoice is None:
            # Mettre à jour la colonne envoyee de la table 'Stock'
            obj = Stock.objects.filter(
                reference=invoice_notsend.reference)
            if obj:
                for x in obj:
                    x.envoyee = False
                    x.response = "Pas de mouvement, problème du côté de QuickSoft"
                    x.save()

            print("====> ERREUR, Erreur de création du fichier Json, le mouvement ou donnée incorrect générée par QuickSoft, Réf {}".format(invoice_notsend.reference))
        elif not auth.is_connected or not auth.token:
            # Mettre à jour la colonne envoyee de la table 'Stock'
            obj = Stock.objects.filter(
                reference=invoice_notsend.reference)
            if auth._msg:
                if obj:
                    for x in obj:
                        x.envoyee = False
                        x.response = "ERREUR d'accès au serveur de l'OBR, {}".format(auth._msg)
                        x.save()
            else:
                if obj:
                    for x in obj:
                        x.envoyee = False
                        x.response = "ERREUR de connexion à l'API de l'OBR"
                        x.save()
            
            print("====> ERREUR d'authentification à l'API de l'OBR")
        else:
            # Mettre à jour la colonne envoyee de la table 'Stock'
            obj = Stock.objects.filter(
                reference=invoice_notsend.reference)
            if obj:
                for x in obj:
                    x.envoyee = False
                    x.response = "Problème survenue lors de l'envoie de la facture"
                    x.save()

            print("====> ERREUR innattendue pour l'envoi du mouvement Réf {}, veuillez contacter votre fournisseur de logiciel".format(invoice_notsend.reference))

