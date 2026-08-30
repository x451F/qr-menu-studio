"""Demo content for the seed command. Realistic French menus with edge cases:
long dish names, missing descriptions, missing English translations, two-size prices,
sold-out items, allergens and diets.

Item tuple: (name_fr, name_en, desc_fr, desc_en, prices, allergens, diets, flags)
  prices: list of (label_fr, label_en, "12,50") — label "" for a single price
  flags: set of {"sold_out", "photo:<file stem in seed_assets/photos>"}

Photos and logos live in menus/seed_assets/ (see CREDITS.md); PHOTOS / LOGOS at the bottom map
restaurants and items to those files. Optional restaurant keys: color_mode, languages.
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

# ---------------------------------------------------------------------------------------------
# Helpers for the larger menus below.
# ---------------------------------------------------------------------------------------------
def SIZES(junior, normal):  # noqa: N802  pizza sizes
    return [("Junior", "Junior", junior), ("Normale", "Regular", normal)]


def GLASS(glass, bottle):  # noqa: N802
    return [("Verre", "Glass", glass), ("Bouteille", "Bottle", bottle)]


def CL(a, b, la="25 cl", lb="50 cl"):  # noqa: N802
    return [(la, la, a), (lb, lb, b)]


def PORTION(small, large):  # noqa: N802
    return [("Petite", "Small", small), ("Grande", "Large", large)]


def item(fr, en, desc_fr, desc_en, prices, allergens=(), diets=(), *flags):
    return (fr, en, desc_fr, desc_en, prices, list(allergens), list(diets), set(flags))


SOFT = ["vegan", "vegetarian", "gluten_free"]

# ---------------------------------------------------------------------------------------------
# Trattoria / pizzeria: ~80 items, two-size prices, long names, many missing descriptions.
# ---------------------------------------------------------------------------------------------
GINO = {
    "name": "Chez Gino",
    "slug": "chez-gino",
    "tagline": ("Pizzas au feu de bois et pâtes fraîches, depuis 1994", "Wood-fired pizzas and fresh pasta since 1994"),
    "theme": "trattoria",
    "brand_color": "#2f6f3e",
    "accent_color": "#c8412b",
    "address": "12 avenue Alsace-Lorraine\n19000 Tulle",
    "phone": "05 36 49 01 22",
    "hours": (
        "Lundi – Jeudi : 11h45 – 14h, 18h45 – 22h\nVendredi – Samedi : 11h45 – 14h, 18h45 – 23h\nDimanche : 18h45 – 22h\nVente à emporter : 05 36 49 01 23",
        "Monday – Thursday: 11:45am – 2pm, 6:45pm – 10pm\nFriday – Saturday: 11:45am – 2pm, 6:45pm – 11pm\nSunday: 6:45pm – 10pm\nTakeaway: 05 36 49 01 23",
    ),
    "footer_note": (
        "Pâtes fraîches faites maison. Pizzas sans gluten sur demande (+ 2,00 €). Prix nets, service compris.",
        "Fresh homemade pasta. Gluten-free pizza on request (+ €2.00). Prices include service.",
    ),
    "specials": [
        ("formule", "Formule midi : pizza Junior ou pâtes du jour + boisson", "Lunch set: Junior pizza or pasta of the day + drink",
         "Du lundi au vendredi, hors jours fériés", "Monday to Friday, except public holidays",
         [("Avec boisson", "With drink", "12,50"), ("Avec boisson + café", "With drink + coffee", "14,00")]),
        ("plat", "Escalope milanaise, spaghetti al pomodoro", "Milanese escalope, spaghetti al pomodoro",
         "", "", P("13,90")),
        ("dessert", "Tiramisu maison", "", "Recette de la mamma de Gino", "", P("5,50")),
    ],
    "categories": [
        ("Antipasti", "Starters", "À partager… ou pas", "To share… or not", [
            item("Bruschetta al pomodoro", "Tomato bruschetta", "Pain grillé, tomates, ail, basilic, huile d'olive",
                 "Grilled bread, tomatoes, garlic, basil, olive oil", P("6,50"), ["gluten"], ["vegan", "vegetarian"]),
            item("Burrata des Pouilles, tomates cerises et basilic", "Apulian burrata, cherry tomatoes and basil", "", "",
                 P("11,50"), ["milk"], ["vegetarian", "gluten_free"]),
            item("Carpaccio de bœuf, roquette, copeaux de parmesan", "Beef carpaccio, rocket, parmesan shavings",
                 "Huile d'olive vierge extra, citron", "Extra virgin olive oil, lemon", P("12,50"), ["milk"], ["gluten_free"]),
            item("Assiette de charcuterie italienne", "Italian cured meats platter",
                 "Jambon de Parme 24 mois, coppa, mortadelle à la pistache, salami piquant",
                 "24-month Parma ham, coppa, pistachio mortadella, spicy salami", P("13,50"), ["nuts", "sulphites"], ["gluten_free"]),
            item("Mozzarella di bufala et tomates anciennes", "Buffalo mozzarella and heirloom tomatoes", "", "",
                 P("10,50"), ["milk"], ["vegetarian", "gluten_free"]),
            item("Arancini au ragoût et à la mozzarella (3 pièces)", "Ragù and mozzarella arancini (3 pieces)",
                 "Boulettes de riz panées, sauce tomate", "Breaded rice balls, tomato sauce", P("8,50"), ["gluten", "eggs", "milk", "celery"]),
            item("Focaccia romarin et fleur de sel", "Rosemary and sea salt focaccia", "", "", P("5,00"), ["gluten"], ["vegan", "vegetarian"]),
            item("Calamars frits, sauce tartare maison", "Fried calamari, homemade tartare sauce",
                 "", "", P("9,50"), ["gluten", "molluscs", "eggs", "mustard"]),
        ]),
        ("Pizzas", "Pizzas", "Junior Ø 26 cm · Normale Ø 33 cm · Cuites au feu de bois", "Junior Ø 26 cm · Regular Ø 33 cm · Wood-fired", [
            item("Margherita", "Margherita", "Tomate, mozzarella fior di latte, basilic", "Tomato, fior di latte mozzarella, basil",
                 SIZES("7,50", "10,50"), ["gluten", "milk"], ["vegetarian"], ),
            item("Marinara", "Marinara", "Tomate, ail, origan, huile d'olive", "Tomato, garlic, oregano, olive oil",
                 SIZES("6,50", "9,00"), ["gluten"], ["vegan", "vegetarian"]),
            item("Reine", "Queen", "Tomate, mozzarella, jambon blanc, champignons", "Tomato, mozzarella, ham, mushrooms",
                 SIZES("9,00", "12,50"), ["gluten", "milk"]),
            item("Napolitaine", "Neapolitan", "Tomate, mozzarella, anchois, câpres, olives noires", "Tomato, mozzarella, anchovies, capers, black olives",
                 SIZES("9,00", "12,50"), ["gluten", "milk", "fish"]),
            item("Quatre fromages", "Four cheeses", "Mozzarella, gorgonzola, chèvre, parmesan", "Mozzarella, gorgonzola, goat cheese, parmesan",
                 SIZES("9,50", "13,50"), ["gluten", "milk"], ["vegetarian"]),
            item("Diavola", "Diavola", "Tomate, mozzarella, salami piquant, poivrons, huile pimentée", "",
                 SIZES("9,50", "13,00"), ["gluten", "milk"]),
            item("Calzone", "Calzone", "Pizza fermée : tomate, mozzarella, jambon, œuf", "Folded pizza: tomato, mozzarella, ham, egg",
                 SIZES("10,00", "13,50"), ["gluten", "milk", "eggs"]),
            item("Végétarienne", "Vegetarian", "Tomate, mozzarella, aubergines, courgettes, poivrons grillés", "Tomato, mozzarella, aubergines, courgettes, grilled peppers",
                 SIZES("9,00", "12,50"), ["gluten", "milk"], ["vegetarian"]),
            item("Chèvre-miel", "Goat cheese and honey", "Crème, mozzarella, chèvre, miel de châtaignier, noix", "",
                 SIZES("9,50", "13,00"), ["gluten", "milk", "nuts"], ["vegetarian"]),
            item("La Corrézienne", "The Corrèze", "Crème, lardons fumés, pommes de terre, oignons, cantal entre-deux",
                 "Cream, smoked bacon, potatoes, onions, Cantal cheese", SIZES("10,00", "13,50"), ["gluten", "milk"]),
            item("Bufala", "Bufala", "Tomates cerises, mozzarella di bufala, roquette, huile d'olive", "",
                 SIZES("10,50", "14,50"), ["gluten", "milk"], ["vegetarian"]),
            item("Parma", "Parma", "Tomate, mozzarella, jambon de Parme, roquette, copeaux de parmesan", "Tomato, mozzarella, Parma ham, rocket, parmesan shavings",
                 SIZES("11,00", "15,00"), ["gluten", "milk"]),
            item("Saumon fumé", "Smoked salmon", "Crème, mozzarella, saumon fumé, citron, aneth", "", SIZES("11,00", "15,00"),
                 ["gluten", "milk", "fish"]),
            item("Burrata, mortadelle et éclats de pistache de Bronte", "Burrata, mortadella and Bronte pistachio pieces",
                 "Base crème, burrata ajoutée à la sortie du four", "", SIZES("12,00", "16,50"), ["gluten", "milk", "nuts"], [], "sold_out"),
            item("La Gino : saucisse italienne, poivrons grillés, oignons rouges, olives noires, œuf et mozzarella",
                 "La Gino: Italian sausage, grilled peppers, red onions, black olives, egg and mozzarella",
                 "La pizza du patron, généreuse !", "", SIZES("11,50", "15,50"), ["gluten", "milk", "eggs"]),
        ]),
        ("Pâtes fraîches", "Fresh pasta", "Petite ou grande portion, toutes faites maison", "Small or large portion, all homemade", [
            item("Spaghetti alla carbonara", "Spaghetti carbonara", "Guanciale, jaune d'œuf, pecorino, poivre noir",
                 "Guanciale, egg yolk, pecorino, black pepper", PORTION("9,50", "13,00"), ["gluten", "eggs", "milk"]),
            item("Tagliatelles bolognaise", "Tagliatelle bolognese", "Ragoût de bœuf mijoté 4 heures", "Beef ragù simmered for 4 hours",
                 PORTION("9,50", "13,00"), ["gluten", "eggs", "celery"]),
            item("Penne all'arrabbiata", "Penne all'arrabbiata", "Tomate, ail, piment, persil", "Tomato, garlic, chilli, parsley",
                 PORTION("8,50", "11,50"), ["gluten"], ["vegan", "vegetarian"]),
            item("Lasagne maison", "Homemade lasagne", "Béchamel, ragoût de bœuf, parmesan", "Béchamel, beef ragù, parmesan",
                 [("", "", "13,50")], ["gluten", "eggs", "milk", "celery"]),
            item("Gnocchi au gorgonzola et aux noix", "Gnocchi with gorgonzola and walnuts", "", "",
                 PORTION("10,50", "14,00"), ["gluten", "milk", "eggs", "nuts"], ["vegetarian"]),
            item("Linguine alle vongole", "Linguine alle vongole", "Palourdes, vin blanc, ail, persil", "",
                 PORTION("12,50", "16,50"), ["gluten", "molluscs", "sulphites"]),
            item("Ravioli ricotta et épinards, beurre de sauge", "Ricotta and spinach ravioli, sage butter", "", "",
                 PORTION("10,00", "13,50"), ["gluten", "eggs", "milk"], ["vegetarian"]),
            item("Tagliatelles aux cèpes de Corrèze et crème de cantal", "Tagliatelle with Corrèze porcini and Cantal cream",
                 "Selon la saison, de septembre à novembre", "", PORTION("12,00", "16,00"), ["gluten", "eggs", "milk"], ["vegetarian"]),
            item("Spaghetti aglio, olio e peperoncino", "Spaghetti aglio, olio e peperoncino", "", "",
                 PORTION("7,50", "10,00"), ["gluten"], ["vegan", "vegetarian"]),
            item("Rigatoni all'amatriciana", "Rigatoni all'amatriciana", "Guanciale, tomate, pecorino", "Guanciale, tomato, pecorino",
                 PORTION("9,50", "13,00"), ["gluten", "milk"]),
        ]),
        ("Plats", "Mains", "", "", [
            item("Risotto pollo e funghi", "Chicken and mushroom risotto", "Riz carnaroli, poulet fermier, champignons, parmesan",
                 "Carnaroli rice, free-range chicken, mushrooms, parmesan", P("15,50"), ["milk", "celery"], ["gluten_free"]),
            item("Escalope milanaise, spaghetti al pomodoro", "Milanese escalope, spaghetti al pomodoro", "", "",
                 P("15,00"), ["gluten", "eggs", "milk"]),
            item("Saltimbocca alla romana", "Saltimbocca alla romana", "Veau, jambon de Parme, sauge, vin blanc",
                 "Veal, Parma ham, sage, white wine", P("17,50"), ["gluten", "milk", "sulphites"]),
            item("Osso buco à la milanaise, polenta crémeuse", "Milanese osso buco, creamy polenta", "Cuisson lente de 3 heures",
                 "Slow-cooked for 3 hours", P("19,50"), ["gluten", "celery", "milk", "sulphites"], [], "sold_out"),
            item("Pavé de saumon grillé, légumes du soleil", "Grilled salmon fillet, sun-dried vegetables", "", "",
                 P("16,50"), ["fish"], ["gluten_free"]),
            item("Parmigiana d'aubergines", "Aubergine parmigiana", "Aubergines, tomate, mozzarella, parmesan", "Aubergines, tomato, mozzarella, parmesan",
                 P("13,50"), ["milk"], ["vegetarian", "gluten_free"]),
        ]),
        ("Salades", "Salads", "", "", [
            item("Caprese", "Caprese", "Tomates, mozzarella, basilic", "Tomatoes, mozzarella, basil", P("9,50"), ["milk"], ["vegetarian", "gluten_free"]),
            item("César à l'italienne", "Italian Caesar", "Poulet grillé, parmesan, croûtons, sauce césar", "",
                 P("13,50"), ["gluten", "eggs", "milk", "fish", "mustard"]),
            item("Chèvre chaud, noix et miel", "Warm goat cheese, walnuts and honey", "Toasts de pain de campagne, mesclun", "",
                 P("12,50"), ["gluten", "milk", "nuts", "mustard"], ["vegetarian"]),
            item("Roquette, tomates séchées et parmesan", "Rocket, sun-dried tomatoes and parmesan", "", "",
                 P("10,50"), ["milk"], ["vegetarian", "gluten_free"]),
        ]),
        ("Desserts", "Desserts", "Faits maison", "Homemade", [
            item("Tiramisu maison", "Homemade tiramisu", "Mascarpone, café, biscuit cuillère, cacao", "Mascarpone, coffee, ladyfingers, cocoa",
                 P("6,50"), ["gluten", "eggs", "milk"], ["vegetarian"]),
            item("Panna cotta, coulis de fruits rouges", "Panna cotta with red berry coulis", "", "",
                 P("6,00"), ["milk"], ["vegetarian", "gluten_free"]),
            item("Affogato al caffè", "Affogato al caffè", "Glace vanille noyée dans un espresso", "Vanilla ice cream drowned in espresso",
                 P("5,50"), ["milk"], ["vegetarian", "gluten_free"]),
            item("Cannoli siciliens à la ricotta", "Sicilian ricotta cannoli", "", "", P("6,50"), ["gluten", "milk", "eggs", "nuts"], ["vegetarian"]),
            item("Fondant au chocolat, crème anglaise", "Chocolate fondant, custard", "", "", P("6,50"), ["gluten", "eggs", "milk"], ["vegetarian"]),
            item("Salade de fruits frais", "Fresh fruit salad", "", "", P("5,50"), [], ["vegan", "vegetarian", "gluten_free"]),
            item("Sorbet citron arrosé de limoncello", "Lemon sorbet with limoncello", "Contient de l'alcool", "Contains alcohol",
                 P("6,00"), [], ["vegan", "vegetarian", "gluten_free"]),
            item("Tarte à la ricotta et aux griottes", "Ricotta and sour cherry tart", "", "", P("6,00"), ["gluten", "eggs", "milk"], ["vegetarian"], "sold_out"),
        ]),
        ("Boissons fraîches", "Soft drinks", "", "", [
            item("Coca-Cola, Coca-Cola Zéro", "Coca-Cola, Coca-Cola Zero", "", "", [("33 cl", "33 cl", "3,50")], [], SOFT),
            item("Orangina", "Orangina", "", "", [("25 cl", "25 cl", "3,50")], [], SOFT),
            item("Limonata et aranciata San Pellegrino", "San Pellegrino lemon and orange soda", "", "", [("33 cl", "33 cl", "3,80")], [], SOFT),
            item("Jus de fruits (orange, ananas, abricot, pomme)", "Fruit juice (orange, pineapple, apricot, apple)", "", "", [("25 cl", "25 cl", "3,80")], [], SOFT),
            item("Thé glacé maison à la pêche", "Homemade peach iced tea", "", "", CL("3,80", "5,50", "25 cl", "40 cl"), [], SOFT),
            item("Eau minérale plate ou gazeuse San Pellegrino", "San Pellegrino still or sparkling water", "", "", CL("3,50", "5,50", "50 cl", "1 L"), [], SOFT),
        ]),
        ("Bières", "Beers", "", "", [
            item("Peroni Nastro Azzurro, pression", "Peroni Nastro Azzurro, draught", "", "", CL("4,00", "7,50"), ["gluten"], ["vegan", "vegetarian"]),
            item("Moretti", "Moretti", "", "", [("33 cl", "33 cl", "4,50")], ["gluten"], ["vegan", "vegetarian"]),
            item("Menabrea 1846 ambrée", "Menabrea 1846 amber", "", "", [("33 cl", "33 cl", "5,50")], ["gluten"], ["vegan", "vegetarian"]),
            item("Bière artisanale de Corrèze, blanche", "Corrèze craft wheat beer", "Brasserie de la Vézère", "", [("33 cl", "33 cl", "6,00")], ["gluten"]),
            item("Peroni 0,0 % sans alcool", "Peroni 0.0% alcohol-free", "", "", [("33 cl", "33 cl", "4,00")], ["gluten"]),
        ]),
        ("Vins italiens", "Italian wines", "Verre 12 cl · Bouteille 75 cl", "Glass 12 cl · Bottle 75 cl", [
            item("Chianti Classico DOCG", "Chianti Classico DOCG", "Sangiovese, fruits rouges, tanins soyeux", "Sangiovese, red fruit, silky tannins", GLASS("5,50", "28,00"), ["sulphites"]),
            item("Montepulciano d'Abruzzo", "Montepulciano d'Abruzzo", "", "", GLASS("5,00", "24,00"), ["sulphites"]),
            item("Primitivo di Manduria", "Primitivo di Manduria", "Puissant, fruité, notes de cerise noire", "", GLASS("6,00", "30,00"), ["sulphites"]),
            item("Barolo DOCG", "Barolo DOCG", "Nebbiolo, élevé 3 ans en fût", "", P("54,00"), ["sulphites"]),
            item("Pinot Grigio delle Venezie", "Pinot Grigio delle Venezie", "", "", GLASS("5,00", "24,00"), ["sulphites"]),
            item("Vermentino di Sardegna", "Vermentino di Sardegna", "Frais et minéral", "Fresh and mineral", GLASS("5,50", "26,00"), ["sulphites"]),
            item("Bardolino Chiaretto, rosé", "Bardolino Chiaretto, rosé", "", "", GLASS("5,00", "24,00"), ["sulphites"]),
            item("Prosecco DOC extra dry", "Prosecco DOC extra dry", "", "", GLASS("5,50", "29,00"), ["sulphites"]),
            item("Lambrusco di Sorbara", "Lambrusco di Sorbara", "Pétillant, servi frais", "", GLASS("4,50", "21,00"), ["sulphites"]),
            item("Vin paillé de Corrèze", "Corrèze straw wine", "Vin doux, verre de 6 cl", "", P("7,50"), ["sulphites"]),
        ]),
        ("Apéritifs et digestifs", "Aperitifs and digestifs", "", "", [
            item("Spritz Aperol", "Aperol Spritz", "Aperol, prosecco, eau gazeuse, orange", "Aperol, prosecco, soda, orange", [("", "", "7,50")], ["sulphites"]),
            item("Negroni", "Negroni", "Gin, Campari, vermouth rouge", "Gin, Campari, red vermouth", [("", "", "9,00")], ["sulphites"]),
            item("Limoncello maison", "Homemade limoncello", "", "", [("4 cl", "4 cl", "5,00")]),
            item("Amaretto di Saronno", "Amaretto di Saronno", "", "", [("4 cl", "4 cl", "5,50")], ["nuts"]),
        ]),
        ("Cafés", "Coffee", "", "", [
            item("Espresso", "Espresso", "", "", P("1,80"), [], SOFT),
            item("Café allongé", "Long coffee", "", "", P("2,00"), [], SOFT),
            item("Cappuccino", "Cappuccino", "", "", P("3,50"), ["milk"], ["vegetarian", "gluten_free"]),
            item("Caffè corretto à la grappa", "Caffè corretto with grappa", "", "", P("4,50"), [], SOFT),
            item("Thé ou infusion", "Tea or herbal infusion", "", "", P("3,00"), [], SOFT),
        ]),
    ],
}

# ---------------------------------------------------------------------------------------------
# Gastronomic: few dishes, every one with a photo, long descriptions, no drinks list.
# ---------------------------------------------------------------------------------------------
VIALLE = {
    "name": "Maison Vialle",
    "slug": "maison-vialle",
    "tagline": ("Cuisine d'auteur, produits de Corrèze et d'ailleurs", "Signature cuisine, produce from Corrèze and beyond"),
    "theme": "gastro",
    "color_mode": "dark",
    "brand_color": "#1c2b4a",
    "accent_color": "#b8975a",
    "address": "3 rue de la Barrière\n19000 Tulle",
    "phone": "05 36 49 01 87",
    "hours": (
        "Mercredi – Samedi : 12h15 – 13h30, 19h30 – 21h15\nFermé du dimanche au mardi\nRéservation recommandée",
        "Wednesday – Saturday: 12:15pm – 1:30pm, 7:30pm – 9:15pm\nClosed Sunday to Tuesday\nReservations recommended",
    ),
    "footer_note": (
        "Prix nets, service compris. Menu sans gluten ou végétarien sur demande 48 h à l'avance.",
        "Prices include service. Gluten-free or vegetarian menu available with 48 hours' notice.",
    ),
    "specials": [
        ("formule", "Menu Découverte", "Discovery menu",
         "Le marché du chef en cinq ou sept services, servi à l'ensemble de la table", "The chef's market menu in five or seven courses, served to the whole table",
         [("5 services", "5 courses", "89,00"), ("7 services", "7 courses", "119,00")]),
        ("suggestion", "Accord mets et vins", "Food and wine pairing",
         "Une sélection de vins de petits producteurs français", "A selection of wines from small French producers",
         [("3 verres", "3 glasses", "42,00"), ("5 verres", "5 glasses", "65,00")]),
    ],
    "categories": [
        ("Entrées", "Starters", "", "", [
            item("Tartare de langoustines, céleri-rave, sorbet tomate et citron caviar",
                 "Langoustine tartare, celeriac, tomato sorbet and finger lime",
                 "Langoustines de Bretagne taillées au couteau, purée de céleri-rave fumée, sorbet tomate-basilic",
                 "Hand-cut Breton langoustines, smoked celeriac purée, tomato and basil sorbet",
                 P("32,00"), ["crustaceans", "celery"], ["gluten_free"], "photo:langoustine-tartare"),
            item("Foie gras de canard poêlé, chutney de coing et pain d'épices",
                 "Pan-seared duck foie gras, quince chutney and gingerbread",
                 "Foie gras du Sud-Ouest snacké, jus de volaille corsé, herbes et fleurs du jardin",
                 "", P("36,00"), ["gluten", "sulphites"], [], "photo:foie-gras-seared"),
            item("Carpaccio de bœuf de Corrèze, sorbet poivron et piment d'Espelette",
                 "Corrèze beef carpaccio, red pepper and Espelette chilli sorbet",
                 "Bœuf limousin maturé 30 jours, gressin au sésame, huile d'olive de Nyons",
                 "30-day aged Limousin beef, sesame breadstick, Nyons olive oil",
                 P("28,00"), ["sesame", "gluten"], [], "photo:beef-carpaccio"),
        ]),
        ("Plats", "Mains", "", "", [
            item("Homard breton rôti au beurre demi-sel, risotto crémeux au piment d'Espelette",
                 "Roasted Breton lobster with salted butter, creamy Espelette chilli risotto",
                 "Homard bleu de 600 g, bisque légère, riz carnaroli", "Blue lobster, light bisque, carnaroli rice",
                 P("58,00"), ["crustaceans", "milk", "celery", "sulphites"], ["gluten_free"], "photo:sea-bass-risotto"),
            item("Ris de veau doré, morilles, crème de vin jaune",
                 "Golden veal sweetbreads, morels, vin jaune cream",
                 "Ris de veau de lait croustillant, morilles fraîches, jus corsé",
                 "Crisp milk-fed veal sweetbreads, fresh morels, rich jus",
                 P("48,00"), ["milk", "sulphites", "gluten"], [], "photo:sweetbreads"),
            item("Pigeon de Mauriac rôti, girolles et jus à la fève tonka", "Roasted Mauriac pigeon, girolles and tonka bean jus",
                 "Suprême et cuisse confite, purée de haricots verts, toast de foie de pigeon",
                 "Breast and confit leg, green bean purée, pigeon liver toast",
                 P("46,00"), ["gluten", "milk", "celery", "sulphites"], [], "photo:pigeon", "sold_out"),
        ]),
        ("Desserts", "Desserts", "", "", [
            item("Tatin de pommes du Limousin, chantilly vanille, caramel au beurre salé",
                 "Limousin apple tatin, vanilla chantilly, salted butter caramel",
                 "", "", P("16,00"), ["gluten", "milk", "eggs"], ["vegetarian"], "photo:tarte-tatin"),
            item("Crème au calvados, sorbet à la verveine et praliné de pain brûlé",
                 "Calvados cream, verbena sorbet and burnt bread praline",
                 "Verveine du jardin de la maison", "Verbena from the restaurant's garden",
                 P("16,00"), ["milk", "eggs", "gluten", "nuts"], ["vegetarian"], "photo:calvados-cream-sorbet"),
        ]),
    ],
}

# ---------------------------------------------------------------------------------------------
# Auberge: terroir cooking, pale-yellow brand colour (contrast stress test), a few photos.
# ---------------------------------------------------------------------------------------------
PUY_BLANC = {
    "name": "Auberge du Puy Blanc",
    "slug": "auberge-du-puy-blanc",
    "tagline": ("Cuisine de terroir au coin du feu", "Country cooking by the fireside"),
    "theme": "auberge",
    "brand_color": "#f2dc6b",
    "accent_color": "#4a3218",
    "address": "Le Puy Blanc, D 1120\n19460 Naves",
    "phone": "05 36 49 01 55",
    "hours": (
        "Jeudi – Dimanche : 12h – 14h\nVendredi – Samedi : 19h – 21h30\nOuvert tous les jours en juillet et août",
        "Thursday – Sunday: 12pm – 2pm\nFriday – Saturday: 7pm – 9:30pm\nOpen daily in July and August",
    ),
    "footer_note": (
        "Produits de la ferme et des producteurs voisins. Menu enfant à 9,00 €. Prix nets, service compris.",
        "Produce from the farm and neighbouring producers. Children's menu €9.00. Prices include service.",
    ),
    "specials": [
        ("formule", "Menu du terroir", "Country menu",
         "Entrée, plat, fromage ou dessert. Boissons non comprises.", "Starter, main course, cheese or dessert. Drinks not included.",
         P("24,50")),
        ("plat", "Potée corrézienne", "Corrèze hotpot",
         "Chou, pommes de terre, lard, saucisse et jarret de porc, servie avec le bouillon", "", P("14,50")),
        ("dessert", "Milliard aux cerises", "Cherry milliard", "", "", P("5,50")),
    ],
    "categories": [
        ("Entrées", "Starters", "", "", [
            item("Tourin blanchi à l'ail et au vermicelle", "White garlic soup with vermicelli",
                 "La soupe des veillées, œuf poché", "", P("7,50"), ["gluten", "eggs"], ["vegetarian"]),
            item("Salade de gésiers confits et noix du Périgord", "Confit gizzard salad with Périgord walnuts",
                 "", "", P("11,00"), ["nuts", "mustard", "sulphites"], ["gluten_free"]),
            item("Terrine de campagne, cornichons et confiture d'oignons", "Country terrine, gherkins and onion jam",
                 "Fabriquée à la ferme", "Made on the farm", P("8,50"), ["sulphites"], ["gluten_free"]),
            item("Omelette aux cèpes", "Porcini omelette", "Cèpes ramassés dans les bois voisins", "Porcini picked in the nearby woods",
                 P("12,50"), ["eggs", "milk"], ["vegetarian", "gluten_free"]),
        ]),
        ("Plats", "Mains", "Accompagnés de pommes de terre sarladaises ou de gratin de courge", "Served with Sarlat potatoes or squash gratin", [
            item("Cassoulet de l'auberge", "The inn's cassoulet", "Haricots tarbais, confit de canard, saucisse de Toulouse",
                 "Tarbais beans, duck confit, Toulouse sausage", P("18,50"), ["gluten", "celery"]),
            item("Potée corrézienne", "Corrèze hotpot", "", "", P("16,50"), ["celery"], ["gluten_free"]),
            item("Magret de canard, sauce aux noix", "Duck breast with walnut sauce", "Magret du Périgord, environ 300 g", "", P("21,00"), ["nuts", "milk", "sulphites"]),
            item("Tête de veau sauce gribiche", "Calf's head with gribiche sauce", "", "", P("17,50"), ["eggs", "mustard"], ["gluten_free"]),
            item("Pavé de bœuf limousin grillé, beurre aux cèpes", "Grilled Limousin beef steak with porcini butter", "", "",
                 P("22,00"), ["milk"], ["gluten_free"]),
            item("Chou farci à l'ancienne", "Old-fashioned stuffed cabbage", "", "", P("15,00"), ["gluten", "eggs", "celery"]),
        ]),
        ("Fromages", "Cheese", "", "", [
            item("Cantal entre-deux, salers et bleu d'Auvergne", "Cantal, Salers and Bleu d'Auvergne", "Avec noix et confiture de cerises noires",
                 "With walnuts and black cherry jam", P("8,00"), ["milk", "nuts"], ["vegetarian", "gluten_free"]),
            item("Fromage blanc de la ferme", "Farm fromage blanc", "Miel, crème ou coulis", "", P("5,00"), ["milk"], ["vegetarian", "gluten_free"]),
        ]),
        ("Desserts", "Desserts", "", "", [
            item("Milliard aux cerises noires", "Black cherry milliard", "Spécialité limousine", "Limousin speciality",
                 P("6,50"), ["eggs", "milk", "gluten"], ["vegetarian"]),
            item("Tarte aux noix et miel de châtaignier", "Walnut and chestnut honey tart", "", "",
                 P("7,00"), ["gluten", "eggs", "milk", "nuts"], ["vegetarian"], "sold_out"),
            item("Flognarde aux pommes", "Apple flognarde", "", "", P("6,50"), ["gluten", "eggs", "milk"], ["vegetarian"]),
            item("Crème caramel maison", "Homemade crème caramel", "", "", P("5,50"), ["eggs", "milk"], ["vegetarian", "gluten_free"]),
        ]),
        ("Boissons", "Drinks", "", "", [
            item("Vin de pays de la Corrèze, rouge ou rosé", "Corrèze country wine, red or rosé", "Pichet", "Carafe",
                 [("25 cl", "25 cl", "5,00"), ("50 cl", "50 cl", "9,00")], ["sulphites"]),
            item("Cahors, Clos de Gamot", "Cahors, Clos de Gamot", "", "", GLASS("6,00", "29,00"), ["sulphites"]),
            item("Cidre fermier du Limousin", "Limousin farm cider", "", "", [("33 cl", "33 cl", "4,50")], [], ["vegan", "vegetarian", "gluten_free"]),
            item("Jus de pomme de la ferme", "Farm apple juice", "", "", [("25 cl", "25 cl", "3,50")], [], SOFT),
            item("Eau de source de Corrèze", "Corrèze spring water", "", "", CL("3,00", "4,50", "50 cl", "1 L"), [], SOFT),
            item("Café, décaféiné ou infusion", "Coffee, decaf or herbal tea", "", "", P("2,00"), [], SOFT),
        ]),
    ],
}

DEMO_RESTAURANTS = [BISTRO, GINO, KIOSQUE, VIALLE, PUY_BLANC]

# ---------------------------------------------------------------------------------------------
# Assets. Photos: (French name prefix, file in seed_assets/photos without extension).
# The item whose French name starts with the prefix gets the photo, processed like an upload.
# Items may also carry an explicit "photo:<file>" flag (used above).
# ---------------------------------------------------------------------------------------------
PHOTOS = {
    "bistrot-des-halles": [
        ("Salade de chèvre chaud", "goat-cheese-salad"),
        ("Pâté de tête", "terrine"),
        ("Confit de canard", "duck-confit"),
        ("Filet de truite", "trout-almonds"),
        ("Burger du Bistrot", "burger"),
        ("Assiette de trois fromages", "cheese-board"),
        ("Clafoutis", "clafoutis"),
        ("Moelleux au chocolat", "chocolate-fondant"),
        ("Crème brûlée", "creme-brulee"),
        ("Tarte fine aux pommes", "tarte-tatin"),
    ],
    "chez-gino": [
        ("Bruschetta", "bruschetta"),
        ("Carpaccio de bœuf", "beef-carpaccio"),
        ("Margherita", "pizza-margherita"),
        ("Spaghetti alla carbonara", "carbonara"),
        ("Lasagne", "lasagne"),
        ("Risotto pollo e funghi", "risotto-chicken-mushroom"),
        ("Tiramisu maison", "tiramisu"),
    ],
    "petit-kiosque": [("Croissant", "croissant")],
    "auberge-du-puy-blanc": [
        ("Terrine de campagne", "terrine"),
        ("Cassoulet", "cassoulet"),
    ],
}

# Logos: file in seed_assets/logos. Le Petit Kiosque deliberately has no logo.
LOGOS = {
    "bistrot-des-halles": "bistrot-des-halles.png",
    "chez-gino": "chez-gino.png",
    "maison-vialle": "maison-vialle.png",
    "auberge-du-puy-blanc": "puy-blanc.png",
}


def photo_for(slug: str, name_fr: str, flags=()) -> str | None:
    """Return the seed photo file stem for an item, or None."""
    for flag in flags:
        if flag.startswith("photo:"):
            return flag.removeprefix("photo:")
    for prefix, stem in PHOTOS.get(slug, []):
        if name_fr.startswith(prefix):
            return stem
    return None
