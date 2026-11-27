**English** · [简体中文](dao.zh-CN.md)

# dao timer: a Taoist cyber timer

A gamified timer in crisp, polished 1-bit pixel art (inspired by Soul Knight and Minit), starring a chibi Taoist priest. **The chip is the source of truth for time**: the offline timer inside the chip, wwb timer, keeps counting at all times and survives power loss. dao timer is a controller program (`apps/dao/`) that only handles the show:

- Switch up: a **ritual** (法事) begins: burning incense, drawing talismans, forming hand seals, brewing elixirs, pacing the Dipper...
- Switch down: the priest **rests** (歇): sipping tea, napping, watching clouds, sweeping leaves...

The OLED and the LED matrix carry the performance; the 4-digit display shows the accumulated time.

Current content:

| Category | Count |
|---|---|
| Rituals | 55 |
| Rests | 54 |
| Omens (divination, 起卦) | 9 |
| Special scenes (Opening the Altar, Heaven and Earth Reborn) | 2 |

## Rules

| When | Condition | Plays | Then |
|---|---|---|---|
| Switch up | An unfinished ritual exists | Rest·exit → Ritual·resume → Ritual·sustain | Continue it |
| Switch up | None | (1/3 chance of an omen →) New ritual·enter → sustain | Start a new ritual |
| Switch down | This ritual's total ≥ 10 minutes (accumulated across pauses) | Ritual·complete → Rest·enter → Rest·sustain | Ritual ends, Dao merit +1 |
| Switch down | Under 10 minutes | Ritual·interrupt → Rest·enter → Rest·sustain | Ritual is kept |

- **The sustain phase can run forever.** When one round ends (e.g. a stick of incense burns out), it "renews": the remains are blown away, a fresh stick goes in, and the next round starts.
- **Random picks.** Rituals, rests and omen methods are all drawn at random; the dozen or so most recently used won't repeat.
- **The omen's result** (a six-line hexagram) becomes this ritual's hexagram; some rituals draw it.
- **Changing course mid-transition.** If the switch flips again before a transition finishes, the current segment plays out at ×3 speed and then takes the new route. Scene changes use a 0.35-second dithered dissolve.
- **Opening the Altar (开坛).** Plays when the program starts and takes over the device; shows the cultivation realm and Dao merit.
- **Realm** (境界) is set by total hours: Mortal (凡人), Qi Refining (练气) 1h, Foundation Building (筑基) 10h, Core Formation (结丹) 30h, Nascent Soul (元婴) 80h, Spirit Transformation (化神) 200h, Void Refining (炼虚) 500h, Body Integration (合体) 1000h, Great Ascension (大乘) 2000h, Tribulation (渡劫) 5000h.
- **Heaven and Earth Reborn (天地重开).** Powering on with the switch up makes the chip reset to zero; dao timer then plays Heaven and Earth Reborn, and the ritual and Dao merit are cleared too.
- **BOOT button**: shows realm, Dao merit, total practice time and the current ritual.

## Disconnects and switching hosts

All time comes from the chip (protocol `APP_STATE`; the chip pushes reports on start, stop and reset).

Ritual progress lives in the chip's controller storage (`APP_DATA`), and it is tiny: which ritual is current, the accumulated time when the ritual started, the random seed, the hexagram, Dao merit, and the recently used scenes. It is written only when a new ritual starts, on completion, and on reset.

So if the Raspberry Pi crashes, the cable is pulled, or a different host takes over, reconnecting brings back the same ritual with the same variations, with progress picked up from the chip's time. Starts and stops during a disconnect line up too: for example, if the ritual passed 10 minutes and was stopped while disconnected, it completes immediately on reconnect.

## Running

The simulator (`python -m wwb.sim`, program list on the right of the web page) has three entries:

| Program | Purpose |
|---|---|
| dao timer | The real thing |
| dao timer 快进 (fast-forward) | Ritual progress runs 30× faster: the 10-minute completion takes 20 seconds; for reviewing the flow |
| dao timer 画廊 (gallery) | Plays every scene in turn. Rituals go through the full flow (enter, sustain fast-forwarded for a bit over one round, interrupt, rest, resume, complete). Short-press BOOT for the next scene, long-press to jump to the next category, switch down to pause; the 4-digit display shows the scene number and the scene name appears in the output panel |

```bash
python -m apps.dao [--complete-after 600] [--timescale 1]    # real device, or --port sim
python -m apps.dao_gallery --only r2.zhufu                   # view just one scene
python -m wwb.remote --deploy apps.dao                       # deploy to the Raspberry Pi as a resident service (see raspberrypi.md)
```

A real device must first be flashed with firmware that supports `APP_STATE`.

## Code

```
apps/dao/
  engine/      canvas gfx, pixel tools pix (sprites, outlines, smoke puffs, sparks, screen shake, white flash), the priest chars,
               easing anim, I Ching symbols symbols, Chinese numerals & stems/branches cn, scene base class scene,
               director director (state machine), runtime runtime (live / gallery / output)
               (art / rig are a grayscale renderer that was tried and abandoned; unused now)
  rituals/     rituals (r0_incense.py is the example; r1-r6 one batch each)
  rests/       rests (x1-x6)
  omens/       omens (o_*)
  special/     Opening the Altar, Heaven and Earth Reborn
  tools/       preview (renders contact-sheet PNGs), check (exceptions, timing, missing glyphs, transitions)
  catalog/     per-batch catalogs: each scene's cultural basis, sources, and the content of each phase
  assets/fonts Fusion Pixel pixel font (12px / 8px, GBK subset, OFL license)
  AUTHORING.md scene authoring guide
```

```bash
conda run -n esp32 python -m apps.dao.tools.check            # all scenes, about 70 seconds
conda run -n esp32 python -m apps.dao.tools.preview r1.bell --out /tmp/pv
```

Performance budget: on a PC, median ≤ 3 ms and max ≤ 15 ms per frame, so it runs at 30 fps on a Raspberry Pi Zero 2 W. Currently every scene's median is under 0.7 ms.
check also checks for text stacking: characters overlapping each other, or characters covered by the artwork, count as errors (g.text outlines text in black by default, and text is drawn last).

## Scene catalog

(Generated from the `name` / `desc` in the code; for each scene's basis, sources and per-phase details, see the batch catalogs.)

### Rituals (55)


**r Example** 

| id | Name | Scene |
|---|---|---|
| `r.incense` | Burning incense (燃香) | The priest walks to the offering table, holds up incense and bows three times; three sticks fly into the censer trailing spirit light. The incense burns down with the timer, smoke puffs rise, and when it burns out he offers another |

**r1 Incense, offerings and liturgy** [catalog](../apps/dao/catalog/r1.md)

| id | Name | Scene |
|---|---|---|
| `r1.bell` | Striking the bell (鸣钟) | The priest pulls the rope to strike the bell: eighteen fast, eighteen slow, eighteen in between, twice over for 108 strikes. The bell shudders, sound waves ripple out, and a bird on the beam jumps in fright |
| `r1.flower` | Scattering flowers (散花) | The priest plucks flowers from a basket and tosses them high; each one bursts into bloom with a "pop" (the eleven flowers of the Flower-Scattering Verse), petals spiral down and carpet the ground; after a round a whirlwind sweeps the carpet away |
| `r1.fruit` | Offering fruit (供果) | One by one the priest stacks longevity peaches and honey tangerines onto a tall fruit stand into a tower; sparrows sneak in to steal and are scared off by his sword-finger gesture; after a round the gods accept the offering and the fruit rises as specks of light |
| `r1.joss` | Burning joss treasure (化宝) | The priest tosses paper ingots one after another into a brick furnace; flames leap from the mouth and sparks shoot from the top. He pokes the firebox and gets startled by sparks; after a round new ingots fall from the sky |
| `r1.lamp` | Ever-burning lamp (长明灯) | In a dark hall the priest tends a glass ever-burning lamp: trimming the wick, lowering the curtain with a sword-finger gesture to block the wind. The oil drops with the timer; when it runs dry he tops it up from a pot |
| `r1.memorial` | Burning the memorial (焚表) | With a big brush the priest writes a memorial to heaven character by character on a screen, stamps it with the "道经师宝" (Treasure of the Dao, Scripture and Master) seal when full, and it burns from the bottom up; on completion the ashes turn into a crane and fly away |
| `r1.river` | Floating river lanterns (放河灯) | Under the full moon of the Ghost Festival (中元) night, the priest kneels by the river releasing lotus lanterns one by one; they drift toward the horizon, growing smaller. Fish leap, fireflies glow; after a round a paper Dharma boat sails across the horizon |
| `r1.sprinkle` | Purifying with water (洒净) | At the altar at dawn, the priest dips a willow branch in pure water and flicks it; droplets fan out and splash on the ground as he circles the water bowl, changing direction. He chants the Incantation for Purifying Heaven and Earth; after a round sweet dew pours into the bowl |
| `r1.wine` | Three offerings of wine (三献酒) | At an open-air jiao altar with long banners fluttering, the priest lifts the ewer for the first, second and final offerings; the aroma of wine drifts from the brimming jue cup; after a round he lifts the cup and pours the wine onto the ground |

**r2 Talismans, incantations and seals** [catalog](../apps/dao/catalog/r2.md)

| id | Name | Scene |
|---|---|---|
| `r2.fayin` | Stamping the Dharma seal (盖法印) | The priest presses the "道经师宝" seal into the ink paste twice, leaps up to stamp it, presses left and right; the document floats up to show the red seal, then flies right onto a stack |
| `r2.feifu` | Flying talismans (飞符) | The priest draws talismans from the altar and hurls them; they tumble into the formation and circle its talisman core. Once all nine are in place they become a streak of light shooting into the ninth heaven, and the sky answers with a beam |
| `r2.fushui` | Dissolving a talisman in water (化符入水) | In the courtyard at night, the priest holds a yellow talisman above a bowl of clear water; it burns slowly from the tip toward his fingers, the ash spirals into the bowl and ripples spread. Every so often he traces a secret name on the water with a sword-finger |
| `r2.ganshi` | Corpse herding of Chenzhou (辰州赶尸) | On a scrolling moonlit mountain road, the priest in a bamboo hat leads with a soul-summoning bell held high; two "guests" with yellow talismans on their foreheads hop after him, arms stretched straight out |
| `r2.jinguang` | Golden Light Incantation (金光神咒) | Seated on a cushion, the priest recites the Golden Light Incantation, changing hand seal with each line; the incantation tablet fills in character by character as pixel golden light grows layer by layer behind him. Thunder, little ghosts, and "golden light, appear swiftly" each get their own moment |
| `r2.jingxin` | Heart-Purifying Incantation (净心神咒) | On a moonlit lakeshore, the priest sits on a rock reciting the Heart-Purifying Incantation; each line is written across the night sky character by character. The water mirrors distant hills and the bright moon, and the ripples calm a little more with every line until the lake is flat as a mirror |
| `r2.kaiguang` | Consecrating the statue (开光点睛) | The priest pulls off the red cloth; with a mirror in his left hand he reflects sunlight onto the statue, and with a vermilion brush in his right he dots open its eyes, ears, nose, mouth and heart in turn. When all are open, the statue glows |
| `r2.zhenzhai` | House-guarding talisman (镇宅符) | The priest slaps a house-guarding talisman onto the door with a "pa!" and stands guard. At night little ghosts drift in; the talisman flashes and scatters them into dots. Dawn comes, the rooster crows, and night falls again |
| `r2.zhufu` | Drawing a cinnabar talisman (朱砂画符) | Standing on a footstool, the priest turns to dip into cinnabar, turns back, and writes stroke by stroke the Three Pure Ones head, the decree (敕令), guardian patterns, talisman core and talisman foot; a brush-strike, a sword-finger, the seal, and the finished talisman glows |

**r3 Hand seals, ritual implements and Bugang** [catalog](../apps/dao/catalog/r3.md)

| id | Name | Scene |
|---|---|---|
| `r3.bugang` | Bugang (步罡踏斗, pacing the Big Dipper) | At a starlit altar a star map is laid out; forming a sword seal, the priest walks the Steps of Yu star by star. Ripples spread where he steps, each star lights up underfoot, and the Big Dipper in the sky lights up with it |
| `r3.dizhong` | Ringing the emperor bell (摇帝钟) | The priest holds the emperor bell high and rings it; sound waves spread. A ball of sound-light climbs a nine-step cloud stair one step at a time with the timer, until the Gate of Heaven opens |
| `r3.fuchen` | Waving the horsetail whisk (挥拂尘) | The priest sweeps with his horsetail whisk stroke after stroke, gusts carrying the room's dust out of frame; the taiji in the moon window brightens from dark to light with the timer |
| `r3.hulu` | Gourd captures a demon (葫芦收妖) | The priest aims a big gourd at a glaring cloud of demon qi; it stretches out and spirals into the gourd bit by bit, and little ghosts get yanked in whole; the demon qi shrinks with the timer |
| `r3.lingpai` | Slamming the command token (令牌拍案) | The priest grabs the Five Thunders command token, raises it and slams it on the altar table; the table shakes, dust flies and sparks burst. With the timer, the command flags of the Five Camps fly in one by one into the flag holder |
| `r3.longjiao` | Blowing the dragon horn (吹龙角) | On a cliff the priest puffs his cheeks and blows the dragon horn; the sound rises to heaven. Heavenly soldiers descend one by one on little clouds and line up on three rows of clouds to the right |
| `r3.qixing` | Seven-Star Sword (七星剑) | At night on a stone altar the priest wields the Seven-Star Sword: chop, thrust, sword flourish, sword qi flying out. With the timer the seven stars of the Dipper light up along the blade, and the Dipper in the sky connects with them |
| `r3.shoujue` | Forming hand seals (掐诀) | The priest raises a palm and forms seals; in a close-up frame on the right a big pixel hand forms, in turn, the sword seal, Lingguan seal, Five Thunders seal and Three Mountains seal, each with its effect: sword qi, spirit fire, thunder light, three mountains |
| `r3.zhaoyao` | Demon-revealing mirror (照妖镜) | The priest holds up a bronze mirror at a visitor; the part lit by its beam shows the true form (fox, skeleton, snake). The beam widens with the timer, revealing more and more |

**r4 Inner alchemy, cultivation and exercises** [catalog](../apps/dao/catalog/r4.md)

| id | Name | Scene |
|---|---|---|
| `r4.baduanjin` | Baduanjin (八段锦, Eight Brocades) | In the temple courtyard the priest practices the Eight Brocades form by form: holding up the sky, drawing the bow to shoot the eagle, single-arm raise, looking back, shaking head and wagging tail, touching the toes, clenching fists, seven heel bounces |
| `r4.furnace` | Brewing the elixir (炼丹) | Kneeling at the elixir stove, the priest fans the fire and watches it; the bagua furnace puffs elixir vapor as the fire shifts between gentle and fierce. One turn every ten minutes; at nine turns the golden elixir is done and shoots into the sky |
| `r4.liuzi` | Six Healing Sounds (六字诀) | On a cliff facing a sea of clouds, the priest breathes in clear qi through the nose and exhales one sound through the mouth: xu, he, hu, si, chui, xi (嘘呵呼呬吹嘻); each enlarged character rides a wave of breath toward the clouds |
| `r4.orbit` | Microcosmic orbit (小周天) | In a quiet room the priest sits on a cushion, eyes closed; a point of light rises along the Governing Vessel and descends along the Conception Vessel around his body, flaring as it passes the three gates: Weilü, Jiaji and Yuzhen |
| `r4.sunmoon` | Absorbing sun and moon (采日月) | On a lone peak above a sea of clouds, the priest faces the sun by day to take in its rays and the moon by night to take in its essence; sun and moon rise in the east and set in the west, one round per day and night |
| `r4.taiji` | Taiji boxing (太极拳) | On a stone platform by the lake the priest does taiji boxing; a dotted taiji diagram slowly turns behind him and his hands leave flowing trails: Parting the Wild Horse's Mane, White Crane Spreads Its Wings, Cloud Hands, Single Whip |
| `r4.turtle` | Turtle breathing (龟息) | On a rock by the pond the priest regulates his breath, eyes closed, a goose feather hanging before his nose; an old turtle in the pond stretches its neck to swallow air and pulls it in to hold its breath along with him, as he silently counts to 120 |
| `r4.wuqinxi` | Five Animals Play (五禽戏) | In a forest clearing the priest practices the Five Animals Play; tiger, deer, bear, monkey and crane take turns running over to crouch beside him and follow along. The tiger pounce shakes the ground, the monkey picks peaches, the bird spreads its wings |
| `r4.yuanying` | Forming the core, emerging spirit (结丹出神) | Seated on a lotus throne, light rises from the priest's lower dantian to the middle and upper dantian; the halo behind him grows to three rings, three flowers bloom above his head, and on success the Nascent Soul rises from the crown of his head |

**r5 I Ching images, stars, thunder rites and feng shui** [catalog](../apps/dao/catalog/r5.md)

| id | Name | Scene |
|---|---|---|
| `r5.bagua` | Earlier and Later Heaven (先天后天) | On an octagonal bagua board, the eight trigrams fly one by one from their Earlier Heaven positions to their Later Heaven positions, in the order of the Shuogua commentary ("The Lord comes forth in Zhen ... and completes his word in Gen"); the priest sees them off with whisk and sword-finger |
| `r5.hetu` | Hetu and Luoshu (河图洛书) | A dragon-horse bearing the Hetu and a divine turtle bearing the Luoshu rise from the river; the dots on the tablets appear group by group following the Hetu and the Luoshu. The priest counts them with a sword-finger from the bank, and the mnemonic is written at top left |
| `r5.leifa` | Palm thunder (掌心雷) | Under heavy black clouds, the priest draws lightning into his palm and pushes it out as a horizontal bolt that blasts evil apart; five thunders per round, and after the fifth all five strike together |
| `r5.liangyi` | Taiji gives birth (太极化生) | The priest sits in visualization; before him the taiji splits in two, doubling layer by layer into Fu Xi's sequence diagram of the 64 hexagrams; whichever hexagram the sweep reaches is drawn at bottom right |
| `r5.lidou` | Dipper worship (礼斗) | Before the Dipper altar the priest lifts a candle to light the seven-star lamps; with each lamp, a star of the Big Dipper lights up in the sky and one more star line connects. When all seven are lit, the flames rise to heaven |
| `r5.luopan` | Seeking the dragon (寻龙) | Holding a luopan compass, the priest crosses mountains seeking the dragon vein as the landscape scrolls; at each stop he raises the compass, and in a close-up the heaven dial turns and the needle settles to fix the orientation; finally he plants a flag to mark the spot |
| `r5.qiyu` | Praying for rain (祈雨) | The priest mounts the altar and waves the command flag; clouds gather from both sides to cover the blazing sun, a dragon weaves through them, rain falls on the parched fields, and the seedlings grow and head out with the timer; after the rain the clouds part and a rainbow appears |
| `r5.wuxing` | Five Phases (五行生克) | Five Phase tokens form a generating cycle around a controlling five-pointed star; the phase in season inverts and plays its effect, qi flows along the outer arc to the phase it generates, and every so often a controlling strike lands |
| `r5.xiu` | Stargazing (观星) | On the observatory the priest tends the armillary sphere as the 28 lunar mansions rise from the east one by one: he points one out, turns the sphere to align, and unrolls a scroll to record it; one round covers the full circuit of the heavens |

**r6 Cyber Daoist arts** [catalog](../apps/dao/catalog/r6.md)

| id | Name | Scene |
|---|---|---|
| `r6.binary` | Binary hexagram (二进制卦) | The priest flips DIP switches one by one to count; the hexagram on the CRT counts from Kun (000000) to Qian (111111), overflows and wraps to zero: "Reversal is the movement of the Dao" |
| `r6.codefu` | Code talisman (代码符箓) | At his workstation the priest types code; each finished line makes the plotter on the right draw part of a talisman on paper. Compiles with 0 ERR: "swiftly, as the law commands!" (急急如律令) |
| `r6.gcode` | Robot-arm hand seals (机臂结印) | The priest gestures hand seals and an industrial robot arm beside him copies them, bending its fingers joint by joint per G-code: the sword seal fires sword qi, the fist seal draws in a qi ring, palm thunder throws arcs everywhere |
| `r6.ledincense` | Cyber incense (赛博烧香) | The priest plugs in an electronic censer; three LED incense sticks light up segment by segment and emit digital smoke. He taps an electronic wooden fish, "功德+1" (merit +1), and when it burns out he scans a QR code to top up |
| `r6.livestream` | Livestreamed blessing (直播祈福) | Holding a selfie stick, the priest goes live before the offering table; the danmaku fills with "福生无量天尊" (blessings, Heavenly Worthy of Boundless Life), hearts float up, someone sends a rocket, and the incense meter fills |
| `r6.scope` | Oscilloscope taiji (示波太极) | The priest clips an oscilloscope probe to his topknot and turns the knobs; in X-Y mode a Lissajous circle grows into a taiji stage by stage: wuji, taiji, yang arising, the two modes |
| `r6.tesla` | Thunder rite debugging (雷法除虫) | Sword in hand, the priest commands a Tesla coil; any bug that crawls close is zapped to bits by an arc; when fully charged, five thunders strike together |
| `r6.upload` | Memorial to the cloud (云端上表) | The priest seals the memorial in an envelope and stuffs it into a laptop; a Wi-Fi link carries little envelopes one by one into the Southern Heavenly Gate in the clouds; when the connection drops he holds up his phone hunting for signal |
| `r6.wafer` | Wafer alchemy (晶圆炼丹) | A lithography machine converted from a bagua furnace; the priest fans the fire while the wafer in the round window is exposed die by die in a serpentine path; after nine turns a chip stamped "丹" (elixir) pops out |

### Rests (54)


**x1 Sleep and dreams** [catalog](../apps/dao/catalog/x1.md)

| id | Name | Scene |
|---|---|---|
| `x1.bubble` | Dozing with a snot bubble (打盹冒泡) | In the elixir room the priest dozes by the furnace, a snot bubble swelling and shrinking with each breath, head nodding; the bubble pops, he jolts awake, the master coughs, and he pretends to be diligent again |
| `x1.butterfly` | Zhuangzi's butterfly dream (庄周梦蝶) | Under a big tree the priest sleeps against the trunk, a dream line linking him to a fluttering butterfly; it rests on a flower, lands on his nose, and in a flash man and butterfly swap places (the transformation of things) |
| `x1.chentuan` | Chen Tuan's long sleep (陈抟高卧) | Under the eaves of a stone chamber on Mount Hua, the priest lies on his side, chin in hand (the hibernating-dragon sleep); sun and moon cycle, the seasons turn, and even the crane bringing an imperial summons gets blown away by one big snore |
| `x1.gaomu` | Body like withered wood (形如槁木) | Before a moon window the priest sits at a low table in sitting-forgetting, motionless: grass grows, vines climb, spiderwebs form, a bird builds a nest on his head and hatches eggs; one long exhale and everything scatters |
| `x1.huangliang` | Yellow Millet Dream (黄粱一梦) | In an inn the priest lies on a celadon pillow; a dream bubble plays a whole life like a lantern show (passing the exams, general, chancellor, duke, eighty years old). The dream bursts, he wakes, and the millet on the stove isn't even cooked yet |
| `x1.huaxu` | Wandering in Huaxu (华胥梦游) | In the night sky the priest sleeps curled on an auspicious cloud, ribbons fluttering, as the sea of clouds and immortal mountains floating on it stream past; a white crane flies alongside and the Huaxu archway sweeps by |
| `x1.hugong` | Heaven in a gourd (壶中天) | When the market closes, the priest leaps into the big gourd hanging at the shop front to sleep; the gourd swells and shrinks with his snores, and in the round window on its belly sun and moon cycle; someone upstairs is peeking |
| `x1.stars` | Counting stars lying down (卧数星斗) | On a summer-night hillside the priest lies on his back pointing at the Dipper, counting star by star as names and numbers pop up; he dozes off mid-count, and a shooting star wakes him again |
| `x1.zhenliu` | Pillowed on stone, rinsed by the stream (枕石漱流) | By a stream the priest lies with his head on a rock, bamboo hat over his face, feet crossed, one hand trailing in the water; fish leap, flowers drift by, a dragonfly lands on his toe, and a splash hits his ear and makes the hat jump |

**x2 Qin, chess, calligraphy, painting, tea and wine** [catalog](../apps/dao/catalog/x2.md)

| id | Name | Scene |
|---|---|---|
| `x2.goose` | Trading scripture for geese (写经换鹅) | With a huge brush the priest writes the Huangting Jing character by character on hanging xuan paper while white geese swim in the pond; after two lines he finishes, cages a goose, and leaves |
| `x2.lanke` | The rotten axe handle (烂柯) | The priest leans his axe on a rock and plays go with an immortal boy; sun and moon whirl past, his white beard grows longer and longer, and the axe handle rots and sprouts mushrooms. The game ends, the axe head drops: "why not go?" He swaps in a new axe and starts again |
| `x2.liushang` | Floating wine cups (曲水流觞) | A clear stream winds along; feathered wine cups drift and spin with the current, and when one stops in front of the priest he drinks and writes a poem; if he can't, the penalty is three cups |
| `x2.moon` | Inviting the moon (邀月) | Beside plum blossoms under the moon, the priest drinks alone on a rock, raising his cup to invite the moon, making three with his shadow (the shadow is cast on the ground in real time); now and then he dances, the moon lingers, the shadow scatters |
| `x2.paint` | Painting (丹青) | The priest guides a brush with a sword-finger: distant hills, textured peaks, a waterfall, pines and a fishing boat appear stroke by stroke, and the finished painting comes to life; every third painting is a dragon, and when its eyes are dotted it bursts through the paper and flies away |
| `x2.qin` | Playing the qin (抚琴) | By a pine under the moon, the priest plays the seven-string qin: right hand plucking, left hand pressing the markers with vibrato and slides, strings humming and notes drifting; now and then High Mountains, Flowing Water, or the stringless qin |
| `x2.slips` | Reading scripture (读经) | Reading bamboo slips at night: steadying the scroll, the priest reads the Daodejing and the Zhuangzi character by character, rolling one slip to the right each time he finishes one; a bookworm nibbles the text, and after eating "神仙" (immortal) three times it becomes a Maiwang and floats away |
| `x2.tea` | Brewing tea (煮茶) | Seated before a wind stove, the priest fans and brews tea: three boils (fish eyes, strings of pearls, surging waves), then ladling out, swirling, adding the tea powder, stilling the boil; he pours a bowl and drinks, one line of the Seven Bowls of Tea song per bowl |
| `x2.xiao` | Calling the phoenix with the flute (吹箫引凤) | On a tower reaching into the clouds, the priest leans on the rail playing the xiao flute; the sound spreads, a phoenix with a long tail flies in, circles once, lands on a post, nods, and flies off |

**x3 Landscapes and skies** [catalog](../apps/dao/catalog/x3.md)

| id | Name | Scene |
|---|---|---|
| `x3.cloud` | Watching clouds rise (坐看云起) | The priest sits on a cliff edge watching pixel clouds emerge from the valley one by one, grow, rise and disperse; tired birds return to the mountain, and a little cloud drifts up to him and gets poked apart with a finger |
| `x3.dawn` | Purple qi from the east (紫气东来) | Sunrise over a sea of clouds, rays rotating; three wisps of purple qi flow from the sun into Hangu Pass to the west. The priest salutes the sun from a rock; now and then Laozi rides his green ox through the gate |
| `x3.falls` | Watching the waterfall (观瀑) | A waterfall between two cliffs, water patterns rushing down, white foam churning in the pool and spray flying; the priest watches from a rock by the pool as leaves tumble over the edge, swallows dart through the mist, and a rainbow forms in the spray |
| `x3.fish` | Watching fish from the Hao bridge (濠梁观鱼) | On the stone bridge over the Hao River, the priest (as Zhuangzi) leans on the rail watching fish, with the capped Huizi beside him; five minnows swim at ease while the two go back and forth debating "the joy of fish" |
| `x3.moon` | Gazing at the moon (望月) | In a small pavilion by the river, the priest leans on the rail gazing at the moon, drawn with tonight's real lunar phase; stars twinkle, the moon's reflection shatters into silver, he raises a cup to it, thin clouds drift across, geese fly past |
| `x3.pine` | Wind in the pines (松风) | An old pine on the cliff stretches one long branch over the valley; the priest sits beneath it listening to the wind. In strong gusts the whole canopy bends and springs back and needles fall; a pine cone drops and a squirrel comes out to gnaw it |
| `x3.rain` | Listening to rain (听雨) | Seated under the eaves, the priest listens to the rain: drops fall from the eaves one by one and splash on the stones, the banana leaves quiver under the rain; he drinks tea, frogs croak, distant thunder rolls, a snail climbs the pillar |
| `x3.snow` | Fishing alone on the cold river (寒江独钓) | A thousand mountains under snow; in hat and straw cape the priest fishes from a lone boat. Snow falls in three layers, snow piles up on his hat until he shakes it off; the float bobs, and he mostly pulls up an empty hook |
| `x3.tide` | Watching the tidal bore (观潮) | Standing on the fish-scale stone seawall of the Qiantang River: a single line of tide pushes diagonally across from the horizon, rising higher as it nears, and splashes up when it hits the wall; on three tenths of the waves a tide-rider stands holding a flag |

**x4 Immortal traces and spirit beasts** [catalog](../apps/dao/catalog/x4.md)

| id | Name | Scene |
|---|---|---|
| `x4.cicada` | Cicada shell (蝉蜕) | A big cicada on an old tree trunk sings in bursts while the priest below listens and nods off; now and then it performs "the golden cicada sheds its shell" |
| `x4.crane` | The crane returns to the pillar (鹤归华表) | A red-crowned crane stands atop a ceremonial pillar, preening and calling; the priest passes by and looks up, the crane takes off and circles the city tower, writing Ding Lingwei's poem in the air, then lands back on top |
| `x4.deer` | White deer with lingzhi (白鹿衔芝) | A chibi white deer and the priest under an old pine: the deer blinks, flicks its ears, flips its tail, lowers its head to graze; a lingzhi mushroom breaks through the soil, the priest picks it and feeds the deer, the deer stands holding it, and it turns to light and enters its body |
| `x4.firefly` | Rotting grass becomes fireflies (腐草为萤) | At the edge of the grass on a summer night, the priest sits watching fireflies; a big firefly flaps around and lands on his fingertip, and little fireflies now and then gather into the Li (☲) trigram |
| `x4.fox` | Purple fox worships the Dipper (紫狐拜斗) | At night a wild fox sits before a broken stele and strikes its tail to make fire; wearing a skull, it stands up and bows to the Dipper, and if the skull doesn't fall, poof, it turns into a little priest with its tail still showing |
| `x4.kunpeng` | Kun and Peng (鲲鹏) | The great fish of the Northern Darkness swims underwater, breaches the surface, leaps out and becomes the giant Peng bird; wings spread like clouds hanging from the sky, it beats the water for three thousand li, rides the whirlwind up, then plunges back into the sea as the Kun |
| `x4.qingniu` | Green ox heads west (青牛西去) | The priest rides a big-headed, front-facing chibi green ox slowly westward as distant hills, pines and clouds recede; reading the Daodejing, stopping to graze, a "moo", a butterfly landing on a horn |
| `x4.toad` | Liu Hai plays with the golden toad (刘海戏金蟾) | Dressed as Liu Hai, the priest dangles a string of coins to tease a front-facing three-legged golden toad: its eyes follow the coins, its throat sac puffs, its tongue snaps up a bug; one flick of the pole and the toad leaps, bites the coins and swings a couple of times |
| `x4.turtle` | Dragging its tail in the mud (曳尾涂中) | The priest fishes by the Pu River while a turtle crawls across the mudflat step by halting step, dragging a tail trail; it recalls the turtle shell enshrined in the temple and shakes its head: "I'd rather drag my tail in the mud" |

**x5 Temple daily life** [catalog](../apps/dao/catalog/x5.md)

| id | Name | Scene |
|---|---|---|
| `x5.chop` | Chopping wood (劈柴) | Chopping wood in the backyard: setting the log, swinging the axe, a pause, the split; chips fly and the two halves land on the woodpile; done, he wipes his sweat, drinks water, and carries in another bundle |
| `x5.cook` | Tending the stove (烧火) | Kneeling at the brick stove in the dining hall: feeding sticks into the firebox, puffing his cheeks to blow three times through a blowpipe, flames leaping up; sometimes the smoke blows back and blackens his face, and the pot lid rattles |
| `x5.garden` | Watering with a jar (抱瓮灌园) | The well sweep by the well goes unused; the priest crouches, sinks a jar to scoop water and carries it in his arms to water the vegetables, which grow with each trip; the wind creaks the well sweep and he shakes his head: ashamed to use a machine |
| `x5.hens` | Feeding the chickens (喂鸡) | Scattering grain from a gourd ladle; three hens and a rooster run over to peck grain by grain; the rooster stretches its neck to crow, or freezes into a "wooden rooster" |
| `x5.herbs` | Gathering herbs (采药) | On a cliff ledge with a basket on his back, gathering herbs: digging in the rock cracks with a hoe, pulling plants out by the roots and tossing them in, sometimes finding a lingzhi; a cloud rolls in and swallows him: "deep in the clouds, none knows where" |
| `x5.mend` | Mending the robe (补衲) | At night under an oil lamp, seated, mending a patched robe: squinting to thread the needle, pulling a long thread stitch by stitch, biting off the end and holding it up to the lamp: "great perfection seems flawed" |
| `x5.mill` | Turning the millstone (推磨) | At the tofu mill, pushing the stone mill: walking circles around it pushing the bar, only his upper body showing when he's behind it; soy milk drips into a wooden bucket, and when full he carries it out and swaps in an empty one |
| `x5.sweep` | Sweeping leaves (扫叶) | Sweeping fallen leaves under a ginkgo: the bamboo broom pushes and pulls, the leaves go into a pile, and a gust blows them all away: "decrease and decrease again, until you reach non-action" |
| `x5.water` | Carrying water (挑水) | Walking a mountain path with two wooden buckets on a shoulder pole: distant hills and pines recede, the pole bounces, the water sloshes; a frog jumps out of a bucket and a bird lands on the end of the pole |

**x6 Cyber rest** [catalog](../apps/dao/catalog/x6.md)

| id | Name | Scene |
|---|---|---|
| `x6.buzheng` | Not contending (不争) | In the offline-dinosaur runner game, the priest with gourd and staff walks slowly and never jumps; cacti pass right through him. The little dinosaur rushes up, jumping all the way, and finally hits a cactus: GAME OVER. "Because he does not contend, he is free from blame" |
| `x6.charge` | Plugged in (插电) | The priest sits on a cushion charging, a cable plugged into his back; the battery over his head reaches 99% and stalls, he opens one eye, and the plug pops out on its own: "Better to stop than to fill to the brim" |
| `x6.defrag` | Returning to the root (归根) | Holding tea, the priest sits before an old computer watching disk defragmentation: the blocks all scatter ("the ten thousand things arise together"), the read head sweeps cell by cell moving them back ("I watch their return"), and finally all is neat ("returning to the root is called stillness") |
| `x6.dvd` | Taiji screensaver (太极屏保) | Seated before an old TV, the priest watches a taiji screensaver bounce diagonally; when it nearly hits a corner he leans in, and when it truly lands in the corner he jumps up cheering: "the gate of all mysteries" |
| `x6.fan` | Cooling down (散热) | The priest sits before a desk fan cooling off, drenched in sweat; the temperature drops bit by bit and the fan slowly stops; every so often a stray thought arises and he heats up again: "Movement overcomes cold, stillness overcomes heat" |
| `x6.ping` | Asking heaven (问天) | At a small computer the priest pings the Heavenly Court: the packets fly into the Southern Heavenly Gate in the clouds, scatter, "Request timed out"; he pings his own heart instead, the packet loops around back into his chest, and a heart on the screen starts beating: "Without going out the door, know the whole world" |
| `x6.standby` | Standby (待机) | At night the priest closes his laptop and dozes at a low table; the breathing light on the laptop's front edge takes one breath every seven seconds, and he breathes in and out along with it; now and then eyes peek out of the lid gap, and a moth circles the lamp |
| `x6.xinzhai` | Fasting of the heart (心斋) | A row of stray-thought files hangs on the wall (fame, profit, anger, worry...); the priest takes them down one by one and carries them to the recycle bin; once it's emptied he sits and writes "唯道集虚，虚者心斋" (only the Dao gathers in emptiness; emptiness is the fasting of the heart); then a new stray thought pops up with a "ding" |
| `x6.zuowang` | Sitting in forgetfulness (坐忘) | The priest meditates on a cushion while an "uninstall" progress bar beside him runs backward: the characters for benevolence and righteousness (仁义), then rites and music (礼乐), drift off his head, his body dissolves layer by layer into flying pixels until only the cushion is left: "one with the Great Thoroughfare"; then he reassembles, returning to simplicity |

### Omens (9)


**o Omens (divination)** [catalog](../apps/dao/catalog/o.md)

| id | Name | Scene |
|---|---|---|
| `o.cezi` | Character divination (测字) | A hanging scroll unrolls and the priest writes one character with a big brush; a flash of sword light splits it left and right, and the strokes are counted: left gives the upper trigram, right the lower, and the total gives the moving line |
| `o.coins` | Coin divination (金钱课) | The priest shakes three square-holed coins and tosses them up; they flip, land and bounce in sparks; the backs decide young yang, young yin, old yang or old yin, and six throws make the hexagram |
| `o.dayan` | Yarrow-stalk divination (大衍筮) | Seated at a table the priest sorts yarrow stalks: set aside one of fifty, divide in two, hang one, count off by fours, return the remainder, with the Xici commentary typed out line by line; the eighteen changes fast-forward into a hexagram |
| `o.fuji` | Spirit writing (扶乩) | The priest raises the peachwood planchette and its other fork lifts by itself with spirit light; the planchette trembles as the spirit descends, tracing six lines bottom to top in the sand tray with sand flying, and the oracle names the hexagram |
| `o.guijia` | Turtle-shell divination (龟卜) | A turtle plastron stands on a wooden rack; the priest burns the drilled hollows with a flaming thorn branch; it glows red, smokes, and cracks with a snap into a 卜-shaped omen crack; six cracks make the hexagram |
| `o.jiaobei` | Throwing divination blocks (掷筊) | The priest holds a pair of crescent wooden blocks to his forehead and bows, then throws them; they tumble, land and rock. Holy (圣筊), laughing (笑筊) or yin (阴筊) results decide each line; six throws make the hexagram |
| `o.luopan` | Luopan compass (罗盘) | The needle of a big luopan spins wildly then settles on north-south; the priest gives two flicks with his sword-finger, the heaven dial whirls with sparks flying, clicks to a stop, and the indicator gives the upper and lower trigrams |
| `o.meihua` | Plum blossom divination (观梅占) | An old plum tree in bloom, the priest admiring it beneath; two sparrows fight over a branch, tumble to the ground and fly off in alarm; the priest counts on his fingers from the year, month, day and hour, divides by eight for the trigrams and by six for the moving line |
| `o.qian` | Drawing a fortune stick (求签) | Kneeling on a cushion, the priest shakes the stick cylinder, the sticks rattle, and one jumps out and flips to the ground; it stands up enlarged to show its number, and stick number N is hexagram N |

### Special scenes (2)


**s Special** [catalog](../apps/dao/catalog/o.md)

| id | Name | Scene |
|---|---|---|
| `s.boot` | Opening the Altar (开坛) | The priest flies in on an auspicious cloud and leaps down; white flash, screen shake, sparks everywhere, a halo spinning behind him; "dao timer" slams down letter by letter, then the realm and Dao merit are written and the seal is stamped |
| `s.reset` | Heaven and Earth Reborn (天地重开) | Chaos like a hen's egg with the priest curled asleep inside; he jolts awake, draws an axe and splits it, and the egg separates: the light and clear rises to become a sky full of stars, the heavy and murky sinks to become mountains; the priest holds up the sky and writes "天地重开" (Heaven and Earth Reborn) |
