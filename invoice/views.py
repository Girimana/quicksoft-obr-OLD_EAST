from django.http import HttpResponseRedirect
from .models import Invoice
import json
import requests
from requests.structures import CaseInsensitiveDict
from django.db.models import Q


# ---------------------------------------
class Object:
    """
    Dynamic object for (Invoice and Items)
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
def LoadAndSaveInvoiceFromStringList(lst):
    """
    Load invoice and details from string list (MSSQL)
    """
    if not lst:
        return None, None

    # 1 - Load invoice details data from list items
    invoice_items = []
    for obj in lst:
        # 
        obj_str_item = obj.details.split(';') # MSSQL.table.details column

        item = Object()
        item.item_designation = obj_str_item[0].strip()
        item.item_quantity = obj_str_item[1].strip()
        item.item_price = obj_str_item[2].strip()
        item.item_ct = obj_str_item[3].strip()
        item.item_tl = obj_str_item[4].strip()
        item.item_price_nvat = obj_str_item[5].strip()
        item.vat = obj_str_item[6].strip()
        item.item_price_wvat = obj_str_item[7].strip()
        item.item_total_amount = obj_str_item[8].strip()

        # collect items
        invoice_items.append(item)

    # 2 - Load invoice data from first list
    obj_str_invoice = lst[0].facture.split(';') # MSSQL.table.facture culumn

    invoice = Object()
    invoice.invoice_number = obj_str_invoice[0].strip()
    invoice.invoice_date = obj_str_invoice[1].strip()
    invoice.invoice_type = obj_str_invoice[2].strip()
    invoice.tp_type = obj_str_invoice[3].strip()
    invoice.tp_name = obj_str_invoice[4].strip()
    invoice.tp_TIN = obj_str_invoice[5].strip()
    invoice.tp_trade_number = obj_str_invoice[6].strip()
    invoice.tp_postal_number = obj_str_invoice[7].strip()
    invoice.tp_phone_number = obj_str_invoice[8].strip()
    invoice.tp_address_province = obj_str_invoice[9].strip()
    invoice.tp_address_commune = obj_str_invoice[10].strip()
    invoice.tp_address_quartier = obj_str_invoice[11].strip()
    invoice.tp_address_avenue = obj_str_invoice[12].strip()
    invoice.tp_address_number = obj_str_invoice[13].strip()
    invoice.vat_taxpayer = obj_str_invoice[14].strip()
    invoice.ct_taxpayer = obj_str_invoice[15].strip()
    invoice.tl_taxpayer = obj_str_invoice[16].strip()
    invoice.tp_fiscal_center = obj_str_invoice[17].strip()
    invoice.tp_activity_sector = obj_str_invoice[18].strip()
    invoice.tp_legal_form = obj_str_invoice[19].strip()
    invoice.payment_type = obj_str_invoice[20].strip()
    invoice.invoice_currency  = obj_str_invoice[21].strip()
    invoice.customer_name = obj_str_invoice[22].strip()
    invoice.customer_TIN = obj_str_invoice[23].strip()
    invoice.customer_address = obj_str_invoice[24].strip()
    invoice.vat_customer_payer = obj_str_invoice[25].strip()
    invoice.cancelled_invoice_ref = obj_str_invoice[26].strip()
    invoice.cancelled_invoice = obj_str_invoice[27].strip()
    invoice.invoice_ref = obj_str_invoice[28].strip()
    # invoice.invoice_signature = obj_str_invoice[29].strip()
    invoice.invoice_identifier = obj_str_invoice[29].strip()
    invoice.invoice_signature_date = obj_str_invoice[30].strip()
    invoice.cn_motif = obj_str_invoice[31].strip()
    invoice.invoice_items = invoice_items

    # Convert invoice obect into json format
    invoice_json = json.loads(invoice.toJSON())

    # Save Invoices/Details to json file
    with open('./settings.json', 'r') as file :
    # with open('settings.json', 'r') as file:
        settings = json.load(file)
        # jsonFile = open('{}{}.json'.format(settings['invoice_directory'], invoice.replace("/", "_")), "w")
        jsonFile = open('{}{}.json'.format(settings['invoice_directory'], invoice.invoice_number.replace("/", "_")), "w")
        jsonFile.write(json.dumps(invoice_json))
        jsonFile.close()

    return invoice, invoice_items

# ---------------------------------------
def load_invoice_json_file_by_reference(reference):
    """
    Load invoice from json file by reference (referece is the name of object)
    """
    invoice = None
    with open('./settings.json', 'r') as file :
    # with open('settings.json', 'r') as file:
        settings = json.load(file)
        with open('{}{}.json'.format(settings['invoice_directory'], reference.replace("/", "_")), 'r') as file:
            invoice = json.load(file)

    return invoice, invoice['invoice_items']

# ---------------------------------------
def check_invoice(invoice_identifier, token=None):
    """
    Check if invoice exists
    Protocol http de la méthode: POST
    URL: http://41.79.226.28:8345/ebms_api/getInvoice/
    En-tête
    Authorization:Bearer xxx
    Corps de la requête
    {
        "invoice_identifier":"xxx"
    }
    Champs obligatoires
    invoice_identifier
    """
    # Send invoice (add invoice)
    
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    url = None
    try:
        if token: 
            headers["Authorization"] = "Bearer {}".format(token)
            with open('./settings.json', 'r') as file :
            # with open('settings.json', 'r') as file:
                settings = json.load(file)
            url = settings['url_api_get_invoice']
        else:
            auth = None
            # Load json settings  
            with open('./settings.json', 'r') as file :
            # with open('settings.json', 'r') as file:
                settings = json.load(file)
                if settings:
                    auth = AuthenticationEBMS(settings['username'], settings['password'], settings['url_api_login'])
                    auth.connect() # Connect to endpoint 
                    headers["Authorization"] = "Bearer {}".format(auth.token)
                    url = settings['url_api_get_invoice']
    
        response = requests.post(
            url, 
            data=json.dumps(
                { 
                    "invoice_signature": invoice_identifier
                }
            ),
            headers=headers
        )
        if (response.status_code in [200, 201, 202]):
            return True
    except:
        pass
    
    return False


# ---------------------------------------
def send_invoice_offline():
    """
    Send invoice via API
    """
    # url_next = request.GET['url_next']
    #url_next +="&paramId=" + request.GET['paramId']
    # print("URL_NEXT: {}".format(url_next))

    auth = None
    invoice = None
    invoice_items = None
    
    x = Invoice.objects.filter(Q(envoyee='False') | Q(envoyee__isnull=True))
    for invoice_notsend in x:
        
        try:
            lst = Invoice.objects.filter(reference=invoice_notsend.reference)
            invoice, invoice_items = LoadAndSaveInvoiceFromStringList(lst)
            # invoice, invoice_items = LoadAndSaveInvoiceFromStringList(invoice_notsend)
        except:
            try:
                invoice, invoice_items = load_invoice_json_file_by_reference(invoice_notsend)
            except:
                print("Error, fichier json not created")
                pass

        try:
            with open('settings.json', 'r') as file :
                settings = json.load(file)
                if settings:
                    auth = AuthenticationEBMS(settings['username'], settings['password'], settings['url_api_login'])
                    auth.connect() # Connect to endpoint 
        except:
            # Mettre à jour la colonne envoyee et response de la table 'Invoice'
            if auth : 
                if (auth._msg == "Nom d’utilisateur ou mot de passe incorrect."):
                    obj = Invoice.objects.filter(reference=invoice.invoice_number)
                    for invoice_with_many_articles in obj:
                        invoice_with_many_articles.envoyee = False
                        invoice_with_many_articles.response = auth._msg
                        invoice_with_many_articles.save()

    
        # Check if invoice exists
        checked = check_invoice(invoice.invoice_identifier, auth.token)
        if checked :
            obj = Invoice.objects.filter(reference=invoice.invoice_number)
            for invoice_with_many_articles in obj:
                if (invoice_with_many_articles.envoyee == False) or (invoice_with_many_articles.envoyee == None) :
                    invoice_with_many_articles.envoyee=True
                    invoice_with_many_articles.response = "Facture ajoutée avec succées"
                    invoice_with_many_articles.save()
     
        if auth.is_connected and (checked==False) and invoice and invoice_items:
            try:
                # Load json invoice in '/temps'
                with open('{}{}.json'.format(settings['invoice_directory'], invoice_notsend.reference.replace("/", "_")), 'r') as json_file_invoice:
                    invoice_to_send = json.load(json_file_invoice)
                
                # Send invoice (add invoice)
                url = settings['url_api_add_invoice']
                headers = CaseInsensitiveDict()
                headers["Accept"] = "application/json"
                headers["Authorization"] = "Bearer {}".format(auth.token)
                response = requests.post(
                    url, 
                    data=json.dumps(invoice_to_send),
                    headers=headers
                )
                if (response.status_code in [200, 201, 202]):
                    # Mettre à jour la colonne envoyee de la table 'Invoice'
                    msg = json.loads(response.text)
                    msg = msg['electronic_signature']
                    obj = Invoice.objects.filter(reference=invoice_notsend.reference).first()
                    if obj:
                        obj.envoyee = True
                        obj.response = "Facture ajoutée avec succées"
                        obj.electronic_signature = msg
                        obj.save()
                    print("====> Facture Réf° {} envoyée avec succès à l'OBR".format(invoice_notsend))
                else:
                    # Mettre à jour la colonne envoyee de la table 'Invoice'
                    obj = Invoice.objects.filter(reference=invoice_notsend.reference).first()
                    if obj:
                        obj.envoyee = False
                        obj.save()
                
                    msg = json.loads(response.text)
                    msg = msg['msg']
                    obj = Invoice.objects.filter(reference=invoice.invoice_number).first()
                    if obj:
                        obj.envoyee = False
                        obj.response = msg
                        obj.save()
                    
                    print("====> ERREUR, d'envoi de la facture Réf {} à l'OBR {}".format(invoice_notsend, msg))

            except Exception as e:
                # Mettre à jour la colonne envoyee de la table 'Invoice'
                obj = Invoice.objects.filter(reference=invoice_notsend.reference).first()
                if obj:
                    obj.envoyee = False
                    obj.save()
        
                print("====> ERREUR d'envoi de la facture Réf {} à l'OBR, message: {}".format(invoice_notsend, str(e)))
        
        elif checked:
            # Mettre à jour la colonne envoyee de la table 'Invoice'
            
            print("====> ERREUR, la facture Réf {} est déjà enregistrée à l'OBR".format(invoice_notsend))
        elif invoice is None or invoice_items is None:
            # Mettre à jour la colonne envoyee de la table 'Invoice'
            obj = Invoice.objects.filter(reference=invoice_notsend.reference).first()
            if obj:
                obj.envoyee = False
                obj.save()
        
            print("====> ERREUR, Erreur de création du fichier Json facture ou donnée incorrect générée par QuickSoft, Réf {}".format(invoice_notsend.reference))
        elif not auth or not auth.token:
            # Mettre à jour la colonne envoyee de la table 'Invoice'
            obj = Invoice.objects.filter(reference=invoice_notsend.reference).first()
            if obj:
                obj.envoyee = False
                obj.save()
            
            if auth._msg:
                if obj:
                    obj.response = "ERREUR d'accès au serveur de l'OBR, {}".format(auth._msg)
                    obj.save()
            else:
                if obj:
                    obj.response = "ERREUR de connexion à l'API de l'OBR"
                    obj.save()
        
            print("====> ERREUR d'authentification à l'API de l'OBR")
        else:
            # Mettre à jour la colonne envoyee de la table 'Invoice'
            obj = Invoice.objects.filter(reference=invoice_notsend.reference).first()
            if obj:
                obj.envoyee = False
                obj.save()
        
            print("====> ERREUR innattendue pour l'envoi de la facture, facture Réf {}, veuillez contacter votre fournisseur de logiciel".format(invoice_notsend.reference))



# ---------------------------------------
def send_invoice(request):
    """
    Send invoice via API
    """
    url_next = request.GET['url_next']
    reference = request.GET['reference']
    if request.method == 'GET' and 'paramId' in request.GET:
        url_next +="&paramId=" + request.GET['paramId']
    
    # if request.method == 'GET' and 'reference' in request.GET:
    #     reference = request.GET['reference']
    
    auth = None
    invoice = None
    invoice_items = None

    try:
        lst = Invoice.objects.filter(reference=reference)
        invoice, invoice_items = LoadAndSaveInvoiceFromStringList(lst)
    except:
        try:
            invoice, invoice_items = load_invoice_json_file_by_reference(reference)
        except:
            print("Error, fichier json not created")
            pass

    try:
        with open('settings.json', 'r') as file:
            settings = json.load(file)
            if settings:
                auth = AuthenticationEBMS(settings['username'], settings['password'], settings['url_api_login'])
                auth.connect() # Connect to endpoint 
    
    except:
        # Mettre à jour la colonne envoyee et response de la table 'Invoice'
        if (auth._msg == "Nom d’utilisateur ou mot de passe incorrect."):
            obj = Invoice.objects.filter(reference=invoice.invoice_number)
            for invoice_with_many_articles in obj:
                invoice_with_many_articles.response = auth._msg
                invoice_with_many_articles.save()

    # Check if invoice exists
    checked = check_invoice(invoice.invoice_identifier, auth.token)
    if checked :
        obj = Invoice.objects.filter(reference=invoice.invoice_number)
        for invoice_with_many_articles in obj:
            # if (invoice_with_many_articles.envoyee == False) or (invoice_with_many_articles.envoyee == None) :
            invoice_with_many_articles.envoyee=True
            invoice_with_many_articles.response="Facture ajoutée avec succées"
            invoice_with_many_articles.save()
            
            
    
    if auth.is_connected and (checked==False) and invoice and invoice_items:
        try:
            # Load json invoice in '/temps'
            with open('{}{}.json'.format(settings['invoice_directory'], reference.replace("/", "_")), 'r') as json_file_invoice:
                invoice_to_send = json.load(json_file_invoice)
            
            # Send invoice (add invoice)
            url = settings['url_api_add_invoice']
            headers = CaseInsensitiveDict()
            headers["Accept"] = "application/json"
            headers["Authorization"] = "Bearer {}".format(auth.token)
            response = requests.post(
                url, 
                data=json.dumps(invoice_to_send),
                headers=headers
            )
            if (response.status_code in [200, 201, 202]):
                # Mettre à jour la colonne envoyee de la table 'Invoice'
                msg = json.loads(response.text)
                msg = msg['electronic_signature']
                obj = Invoice.objects.filter(reference=reference).first()
                if obj:
                    obj.envoyee = True
                    obj.response = "Facture ajoutée avec succées"
                    obj.electronic_signature = msg
                    obj.save()
                url_next +="&msg=" + "====> Facture Réf° {} envoyée avec succès à l'OBR".format(reference)
                
                print("====> Facture Réf° {} envoyée avec succès à l'OBR".format(reference))
            else:
                
                msg = json.loads(response.text)
                msg = msg['msg']
                # Mettre à jour la colonne envoyee de la table 'Invoice'
                obj = Invoice.objects.filter(reference=invoice.invoice_number).first()
                if obj:
                    obj.envoyee = False
                    obj.response = msg
                    obj.save()

                url_next +="&msg=" + "====> ERREUR, d'envoi de la facture Réf {} à l'OBR {}".format(reference, msg)

                print("====> ERREUR, d'envoi de la facture Réf {} à l'OBR {}".format(reference, msg))

        except Exception as e:
            url_next +="&msg=" + "====> ERREUR d'envoi de la facture Réf {} à l'OBR, message: {}".format(reference, str(e))

            print("====> ERREUR d'envoi de la facture Réf {} à l'OBR, message: {}".format(reference, str(e)))
    
    elif checked:
        print("====> ERREUR, la facture Réf {} est déjà enregistrée à l'OBR".format(reference))
        url_next +="&msg=" + "====> ERREUR, la facture Réf {} est déjà enregistrée à l'OBR".format(reference)
    elif invoice is None or invoice_items is None:
        print("====> ERREUR, Erreur de création du fichier Json facture ou donnée incorrect générée par QuickSoft, Réf {}".format(reference))
        url_next +="&msg=" + "====> ERREUR, Erreur de création du fichier Json facture ou donnée incorrect générée par QuickSoft, Réf {}".format(reference)
    elif not auth or not auth.token:
        print("====> ERREUR d'authentification à l'API de l'OBR")
        # Mettre à jour la colonne envoyee de la table 'Invoice'
        obj = Invoice.objects.filter(reference=invoice.invoice_number).first()
        if obj:
            obj.envoyee = False
            obj.save()
        if auth._msg:
            url_next +="&msg=" + "====> ERREUR d'accès au serveur de l'OBR, {}".format(auth._msg)
            if obj:
                obj.response = "ERREUR d'accès au serveur de l'OBR, {}".format(auth._msg)
                obj.save()
        else:
            url_next +="&msg=" + "====> ERREUR de connexion à l'API de l'OBR"
            if obj:
                obj.response = "ERREUR de connexion à l'API de l'OBR"
                obj.save()
            
    else:
        print("====> ERREUR innattendue pour l'envoi de la facture, facture Réf {}, veuillez contacter votre fournisseur de logiciel".format(reference))
        url_next +="&msg=" + "====> ERREUR innattendue pour l'envoi de la facture, facture Réf {}, veuillez contacter votre fournisseur de logiciel".format(reference)
    

    return HttpResponseRedirect(url_next)

# ---------------------------------------
def cancel_invoice(request, reference):
    """
    Canbcel invoice via API
    body: {
        "invoice_identifier":"4701354861/ws470135486100027/20220211120214/01929"
    }
    """
    url_next = request.GET['url_next']
    #url_next +="&paramId=" + request.GET['paramId']
    #print("URL_NEXT: {}".format(url_next))

    try:
        # Load invoice json file
        invoice, invoice_items = load_invoice_json_file_by_reference(reference)

        with open('./settings.json', 'r') as file :
        # with open('settings.json', 'r') as file:
            settings = json.load(file)
            if settings:
                auth = AuthenticationEBMS(settings['username'], settings['password'], settings['url_api_login'])
    
        # Connect to endpoint 
        auth.connect()
        
        # Cancel invoice
        url = settings['url_api_cancel_invoice']
        headers = CaseInsensitiveDict()
        headers["Accept"] = "application/json"
        headers["Authorization"] = "Bearer {}".format(auth.token)
        response = requests.post(
            url, 
            data=json.dumps({"invoice_identifier": invoice['invoice_identifier']}),
            headers=headers
        )
        if (response.status_code in [200, 201, 202]):
            # Mettre à jour la colonne envoyee de la table 'Invoice'
            obj = Invoice.objects.filter(reference=reference).first()
            obj.annulee = True
            obj.save()
        
        try:
            msg = json.loads(response.text)
            msg = ", message: " + msg['msg']
            url_next +="&msg=" + msg
        except:
            try:
                msg = json.loads(response.content)
                msg = ", message: " + msg['msg']
                url_next +="&msg=" + msg
            except Exception as e:
                msg = ", message: " + str(e)
                url_next +="&msg=" + msg

            print("====> Facture Réf° {} annulée avec succès à l'OBR".format(reference))
        else:
            try:
                msg = json.loads(response.text)
                msg = ", message: " + msg['msg']
            except:
                try:
                    msg = json.loads(response.content)
                    msg = ", message: " + msg['msg']
                except Exception as e:
                    msg = ", message: " + str(e)
    
            print("====> ERREUR d'annulation de la facture Réf {} à l'OBR {}".format(reference, msg))
            
    except Exception as e:
        print("====> ERREUR d'annulation de la facture Réf {} à l'OBR, message: ".format(reference, str(e)))
        try:
            msg = json.loads(response.text)
            msg = ", message: " + msg['msg']
            url_next +="&msg=" + msg
        except:
            try:
                msg = json.loads(response.content)
                msg = ", message: " + msg['msg']
                url_next +="&msg=" + msg
            except Exception as e:
                msg = ", message: " + str(e)
                url_next +="&msg=" + msg

    return HttpResponseRedirect(url_next)

def check_TIN(request):
    
    # check if TIN is valid or not
    url_next = request.GET['url_next']
    nif = request.GET['numNif']
    
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    url = None
    try:
        auth = None
            # Load json settings  
        with open('settings.json', 'r') as file :
            settings = json.load(file)
            if settings:
                auth = AuthenticationEBMS(settings['username'], settings['password'], settings['url_api_login'])
                auth.connect() # Connect to endpoint 
                headers["Authorization"] = "Bearer {}".format(auth.token)
                url = settings['url_api_verify_nif']
            
        response = requests.post(
            url, 
            data=json.dumps(
                { 
                    "tp_TIN": nif
                }
            ),
            headers=headers
        )
        if (response.status_code in [200, 201, 202]):

            customer_name = json.loads(response.text)['result']['taxpayer'][0]['tp_name'] 
            
            url_next += "&valid=True&customer_name=" + customer_name

            return HttpResponseRedirect(url_next)

    except:
        pass
    if auth.is_connected == False:
        url_next += "&connect=false"
    else:
        url_next += "&connect=true"
    url_next += "&valid=False"
    return HttpResponseRedirect(url_next)
