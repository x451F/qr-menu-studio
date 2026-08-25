"""Demo content for the seed command. Realistic French menus with edge cases:
long dish names, missing descriptions, missing English translations, two-size prices,
sold-out items, allergens and diets.

Item tuple: (name_fr, name_en, desc_fr, desc_en, prices, allergens, diets, flags)
  prices: list of (label_fr, label_en, "12,50") — label "" for a single price
  flags: set of {"sold_out"}
"""

P = lambda amount: [("", "", amount)]  # noqa: E731  single unlabeled price

BISTRO = {
    "name": "Le Bistrot des Halles",
    "slug": "bistrot-des-halles",
    "tagline": ("Cuisine du marché, produits de Corrèze", "Market cuisine, produce from Corrèze"),
    "theme": "bistro",
    "brand_color": "#7a2e2a",
    "accent_color": "#c8963e",
    "address": "12 place Martial Brigouleix\n19000 Tulle",
    "phone": "05 55 26 12 34",
    "hours": (
        "Mardi – Samedi : 12h – 14h, 19h – 22h\nDimanche : 12h – 14h30\nFermé le lundi",
        "Tuesday – Saturday: 12pm – 2pm, 7pm – 10pm\nSunday: 12pm – 2:30pm\nClosed on Mondays",
    ),
    "footer_note": (
        "Prix nets, service compris. Viandes d'origine France. Liste des allergènes disponible sur demande.",
        "Prices include service. French-origin meat. Full allergen information available on request.",
    ),
    "specials": [
        ("plat", "Blanquette de veau à l'ancienne, riz pilaf", "Old-fashioned veal blanquette, pilaf rice",
         "Veau du Limousin, carottes, champignons de Paris", "Limousin veal, carrots, button mushrooms", P("15,50")),
        ("formule", "Formule du midi", "Lunch set menu",
         "Entrée + plat ou plat + dessert, du mardi au vendredi", "Starter + main or main + dessert, Tuesday to Friday",
         [("Entrée + plat", "Starter + main", "19,50"), ("Entrée + plat + dessert", "Starter + main + dessert", "23,90")]),
    ],
    "categories": [
        ("Entrées", "Starters", "", "", [
            ("Œuf parfait à 64 °C, crème de cèpes et mouillettes de pain de campagne toastées",
             "64 °C slow-cooked egg, porcini cream and toasted country bread soldiers",
             "Cèpes du Limousin selon la saison", "Limousin porcini, when in season",
             P("11,50"), ["eggs", "milk", "gluten"], ["vegetarian"], set()),
            ("Pâté de tête maison, pickles de légumes", "Homemade head cheese, pickled vegetables",
             "", "", P("9,00"), ["mustard", "sulphites"], [], set()),
            ("Salade de chèvre chaud au miel de châtaignier", "Warm goat cheese salad with chestnut honey",
             "Crottin de chèvre, noix, mesclun, vinaigrette à l'huile de noix", "Goat cheese, walnuts, mixed leaves, walnut oil dressing",
             P("10,50"), ["milk", "nuts", "gluten", "mustard"], ["vegetarian"], set()),
            ("Terrine de foie gras de canard, chutney de figues", "Duck foie gras terrine, fig chutney",
             "Brioche toastée", "Toasted brioche", P("16,00"), ["gluten", "eggs", "milk", "sulphites"], [], set()),
            ("Velouté de potimarron", "Red kuri squash soup",
             "Graines de courge torréfiées, huile de noisette", "Toasted pumpkin seeds, hazelnut oil",
             P("8,50"), ["nuts"], ["vegetarian", "vegan", "gluten_free"], set()),
            ("Six escargots de Bourgogne au beurre persillé", "Six Burgundy snails in parsley butter",
             "", "", P("12,00"), ["molluscs", "milk"], ["gluten_free"], set()),
        ]),
        ("Plats", "Mains", "Garnitures au choix : frites maison, purée ou salade", "Choice of side: homemade fries, mash or salad", [
            ("Tête de veau sauce gribiche, pommes vapeur", "Calf's head with gribiche sauce, steamed potatoes",
             "Spécialité de la maison depuis 1987", "House speciality since 1987",
             P("19,50"), ["eggs", "mustard"], ["gluten_free"], set()),
            ("Pavé de bœuf limousin, sauce au poivre", "Limousin beef steak, pepper sauce",
             "Environ 250 g, cuisson au choix", "About 250 g, cooked to order",
             P("24,00"), ["milk", "sulphites"], ["gluten_free"], set()),
            ("Confit de canard du Périgord, pommes sarladaises à la graisse de canard et salade verte à l'huile de noix",
             "Périgord duck confit, Sarlat-style potatoes cooked in duck fat and green salad with walnut oil",
             "", "", P("21,00"), ["nuts"], ["gluten_free"], set()),
            ("Filet de truite de Corrèze, beurre blanc", "Corrèze trout fillet, beurre blanc",
             "Truite fario de la pisciculture de Beaulieu, légumes de saison", "Brown trout from Beaulieu fish farm, seasonal vegetables",
             P("20,50"), ["fish", "milk", "sulphites"], ["gluten_free"], {"sold_out"}),
            ("Risotto crémeux aux champignons des bois", "Creamy wild mushroom risotto",
             "Parmesan affiné 24 mois", "24-month aged parmesan", P("17,50"), ["milk", "celery"], ["vegetarian", "gluten_free"], set()),
            ("Burger du Bistrot", "Bistrot burger",
             "Bœuf limousin, cantal entre-deux, oignons confits, frites maison", "Limousin beef, Cantal cheese, candied onions, homemade fries",
             P("18,00"), ["gluten", "milk", "eggs", "sesame", "mustard"], [], set()),
            ("Assiette végétale du moment", "",
             "Légumes rôtis, houmous de pois chiches, quinoa, pickles", "",
             P("16,00"), ["sesame"], ["vegetarian", "vegan", "gluten_free"], set()),
            ("Andouillette AAAAA de Troyes, sauce moutarde à l'ancienne", "AAAAA Troyes andouillette sausage, wholegrain mustard sauce",
             "", "", P("18,50"), ["mustard", "milk", "sulphites"], [], set()),
        ]),
        ("Fromages", "Cheese", "", "", [
            ("Assiette de trois fromages affinés de la fromagerie Bordas", "Three matured cheeses from Bordas cheese shop",
             "Selon arrivage", "Depending on availability", P("9,00"), ["milk"], ["vegetarian"], set()),
            ("Fromage blanc à la crème ou au coulis", "Fromage blanc with cream or fruit coulis",
             "", "", P("6,00"), ["milk"], ["vegetarian", "gluten_free"], set()),
        ]),
        ("Desserts", "Desserts", "Faits maison", "Homemade", [
            ("Clafoutis aux cerises noires", "Black cherry clafoutis",
             "La recette de notre grand-mère", "Our grandmother's recipe", P("8,00"), ["eggs", "milk", "gluten"], ["vegetarian"], set()),
            ("Moelleux au chocolat noir, cœur coulant, glace vanille de Madagascar", "Molten dark chocolate cake, Madagascar vanilla ice cream",
             "Prévoir 12 minutes de cuisson", "Allow 12 minutes of baking", P("9,50"), ["eggs", "milk", "gluten", "soy"], ["vegetarian"], set()),
            ("Crème brûlée à la vanille", "Vanilla crème brûlée", "", "", P("7,50"), ["eggs", "milk"], ["vegetarian", "gluten_free"], set()),
            ("Tarte fine aux pommes, caramel au beurre salé", "Thin apple tart, salted butter caramel",
             "", "", P("8,50"), ["gluten", "milk", "eggs"], ["vegetarian"], set()),
            ("Café gourmand", "Coffee with mini desserts", "Espresso et trois mignardises", "Espresso and three petits fours",
             P("9,00"), ["gluten", "milk", "eggs", "nuts"], ["vegetarian"], set()),
            ("Sorbets artisanaux, deux boules", "Artisan sorbets, two scoops",
             "Cassis, poire, citron", "Blackcurrant, pear, lemon", P("6,50"), [], ["vegan", "vegetarian", "gluten_free"], set()),
        ]),
        ("Vins", "Wines", "Le verre 12 cl, la bouteille 75 cl", "Glass 12 cl, bottle 75 cl", [
            ("Coteaux de la Vézère, rouge, domaine de la Mégénie", "Coteaux de la Vézère, red, Domaine de la Mégénie",
             "", "", [("Verre", "Glass", "5,50"), ("Bouteille", "Bottle", "28,00")], ["sulphites"], ["vegan", "vegetarian"], set()),
            ("Cahors, Château Lagrézette 2019", "Cahors, Château Lagrézette 2019",
             "Malbec, tanins fondus", "Malbec, soft tannins", [("Verre", "Glass", "7,00"), ("Bouteille", "Bottle", "36,00")], ["sulphites"], [], set()),
            ("Bergerac blanc sec", "Dry white Bergerac", "", "", [("Verre", "Glass", "5,00"), ("Bouteille", "Bottle", "24,00")], ["sulphites"], [], set()),
            ("Vin paillé de Queyssac-les-Vignes", "Queyssac-les-Vignes straw wine",
             "Vin doux corrézien, le verre de 6 cl", "Sweet Corrèze wine, 6 cl glass", P("8,50"), ["sulphites"], [], set()),
        ]),
        ("Bières & softs", "Beers & soft drinks", "", "", [
            ("Bière pression blonde", "Draught lager", "", "", [("25 cl", "25 cl", "4,00"), ("50 cl", "50 cl", "7,50")], ["gluten"], ["vegan", "vegetarian"], set()),
            ("Bière artisanale de Corrèze, IPA", "Craft IPA from Corrèze", "Brasserie de la Vézère, 33 cl", "Vézère brewery, 33 cl",
             P("6,50"), ["gluten"], [], set()),
            ("Limonade artisanale", "Craft lemonade", "", "", P("4,00"), [], ["vegan", "vegetarian", "gluten_free"], set()),
            ("Jus de pomme du Limousin", "Limousin apple juice", "", "", P("4,50"), [], ["vegan", "vegetarian", "gluten_free"], set()),
            ("Eau minérale plate ou gazeuse", "Still or sparkling mineral water", "",
             "", [("50 cl", "50 cl", "4,00"), ("1 L", "1 L", "6,00")], [], ["vegan", "vegetarian", "gluten_free"], set()),
        ]),
        ("Boissons chaudes", "Hot drinks", "", "", [
            ("Espresso", "Espresso", "", "", P("2,20"), [], ["vegan", "vegetarian", "gluten_free"], set()),
            ("Café crème", "Café crème", "", "", P("3,50"), ["milk"], ["vegetarian", "gluten_free"], set()),
            ("Thés et infusions Dammann", "Dammann teas and infusions", "", "", P("3,80"), [], ["vegan", "vegetarian", "gluten_free"], set()),
        ]),
    ],
}

KIOSQUE = {
    "name": "Le Petit Kiosque",
    "slug": "petit-kiosque",
    "tagline": ("Café du quai", "Riverside café"),
    "theme": "cafe",
    "brand_color": "#2f5d50",
    "accent_color": "",
    "address": "Quai Baluze\n19000 Tulle",
    "phone": "06 12 34 56 78",
    "hours": ("Tous les jours : 8h – 18h", "Every day: 8am – 6pm"),
    "footer_note": ("Prix nets.", "Prices include service."),
    "specials": [],
    "categories": [
        ("Carte", "Menu", "", "", [
            ("Café", "Coffee", "", "", P("1,80"), [], ["vegan"], set()),
            ("Chocolat chaud maison", "Homemade hot chocolate", "", "", P("3,50"), ["milk"], ["vegetarian"], set()),
            ("Croissant pur beurre", "Butter croissant", "", "", P("1,40"), ["gluten", "milk", "eggs"], ["vegetarian"], set()),
            ("Tartine beurre-confiture", "Bread with butter and jam", "Pain au levain de la boulangerie Jarrige", "", P("3,00"), ["gluten", "milk"], ["vegetarian"], set()),
            ("Jus d'orange pressé", "Freshly squeezed orange juice", "", "", [("25 cl", "25 cl", "4,00"), ("40 cl", "40 cl", "5,50")], [], ["vegan"], set()),
        ]),
    ],
}

DEMO_RESTAURANTS = [BISTRO, KIOSQUE]
