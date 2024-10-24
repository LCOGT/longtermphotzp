
import longtermphotzp.atlasrefcat2 as refcat2
REFCAT2_URL = 'http://phot-catalog.lco.gtn/'


def test_fetchcatalog():
    referencecatalog = refcat2.atlas_refcat2(REFCAT2_URL)
    cat = referencecatalog.get_reference_catalog(10,10,0.1)
    assert len(cat) == 65
    assert len (cat.columns) == 16

def test_johnsoncousinsconversion():
    referencecatalog = refcat2.atlas_refcat2(REFCAT2_URL)
    cat = referencecatalog.get_reference_catalog(10,10,0.1, generateJohnson=True)

    print ("\n", cat)
    assert len(cat) == 65
    assert len (cat.columns) == 16 + 2*len(referencecatalog.JohnsonCousin_filters)




