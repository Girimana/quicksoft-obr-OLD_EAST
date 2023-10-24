from django.db import models

class Stock(models.Model):
    """
    Modele Mouvement Stock Obr (QuikSoft)
    """
    reference = models.CharField(db_column='Reference', max_length=100, db_collation='French_CI_AS', blank=True, null=True)
    stock = models.CharField(db_column='Stock', max_length=1024, db_collation='French_CI_AS', blank=True, null=True)
    envoyee = models.BooleanField(db_column='Envoyee', default=False)
    annulee = models.BooleanField(db_column='Annulee', default=False)
    response = models.CharField(db_column='Response', max_length=1000, db_collation='French_CI_AS', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'StockObr'

    def __str__(self):
        return self.reference