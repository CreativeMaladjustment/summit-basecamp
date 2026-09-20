// Placeholder syndicate, fixture and roster data, carried over from the design
// export. Player names, numbers, stats and fixture dates are invented; swap in
// the real roster and the published fixture list when they exist.

export const me = 'u_you';

export const members = {
  u_you:   { id: 'u_you',   name: 'You',   initials: 'YO', colour: '#134E48' },
  u_jason: { id: 'u_jason', name: 'Jason', initials: 'JM', colour: '#1D6960' },
  u_sarah: { id: 'u_sarah', name: 'Sarah', initials: 'SK', colour: '#C84B31' },
  u_alice: { id: 'u_alice', name: 'Alice', initials: 'AR', colour: '#8A6D1F' },
  u_bob:   { id: 'u_bob',   name: 'Bob',   initials: 'BT', colour: '#3F5C58' },
};

export const syndicates = [
  {
    id: 'syn_north',
    name: 'North Stand Syndicate',
    seats: [
      { number: 3, section: '114', row: '8' },
      { number: 4, section: '114', row: '8' },
    ],
    memberIds: ['u_you', 'u_jason', 'u_sarah', 'u_alice', 'u_bob'],
    invitedBy: 'Jason M.',
    holds: '2 seats · Sec 114, Row 8',
  },
  {
    id: 'syn_rail',
    name: 'Rail Line Collective',
    seats: [{ number: 11, section: '102', row: '3' }],
    memberIds: ['u_you', 'u_bob'],
    invitedBy: 'Bob T.',
    holds: '1 seat · Sec 102, Row 3',
  },
];

// Tickets are tracked by year, from the first season to the next.
export const seasons = [
  { year: 2026, label: '2026 Season', packageCents: 248000, current: true },
  { year: 2025, label: '2025 Season', packageCents: 231000, current: false },
];

// Weighted price distribution: a rivalry weekend match carries more of the
// package than a standard midweek one.
export const tiers = {
  rivalry:  { label: 'Rivalry', weight: 1.6, colour: 'gold' },
  standard: { label: 'Standard', weight: 1.0, colour: 'mute' },
  cup:      { label: 'Cup', weight: 1.3, colour: 'green' },
};

export const fixtures = [
  {
    id: 'fx_por', season: 2026, opponentId: 'op_por', opponent: 'Portland Thorns',
    short: 'Portland', kickoff: '2026-09-26T19:30:00', venue: 'Summit Park',
    tier: 'rivalry', valueCents: 19000,
    seats: [
      { number: 3, holder: 'u_you', status: 'confirmed' },
      { number: 4, holder: 'u_sarah', status: 'confirmed' },
    ],
  },
  {
    id: 'fx_bay', season: 2026, opponentId: 'op_bay', opponent: 'Bay FC',
    short: 'Bay', kickoff: '2026-10-03T14:00:00', venue: 'Summit Park',
    tier: 'standard', valueCents: 11500,
    seats: [
      { number: 3, holder: 'u_jason', status: 'confirmed' },
      { number: 4, holder: null, status: 'bench', benchNoteId: 'bn_bay' },
    ],
  },
  {
    id: 'fx_acf', season: 2026, opponentId: 'op_acf', opponent: 'Angel City FC',
    short: 'Angel City', kickoff: '2026-10-18T18:00:00', venue: 'Summit Park',
    tier: 'rivalry', valueCents: 18000,
    seats: [
      { number: 3, holder: 'u_alice', status: 'confirmed' },
      { number: 4, holder: null, status: 'listed', askCents: 9500 },
    ],
  },
  {
    id: 'fx_utah', season: 2026, opponentId: null, opponent: 'Utah Royals',
    short: 'Utah', kickoff: '2026-10-29T19:00:00', venue: 'Summit Park',
    tier: 'standard', valueCents: 9500,
    seats: [
      { number: 3, holder: null, status: 'bench' },
      { number: 4, holder: null, status: 'bench' },
    ],
  },
  {
    id: 'fx_kc', season: 2026, opponentId: null, opponent: 'Kansas City Current',
    short: 'KC', kickoff: '2026-09-12T19:30:00', venue: 'Summit Park',
    tier: 'standard', valueCents: 11000,
    seats: [
      { number: 3, holder: 'u_you', status: 'confirmed' },
      { number: 4, holder: 'u_bob', status: 'confirmed' },
    ],
  },
];

// Thread on a released seat: a note plus replies, not a full chat.
export const benchNotes = [
  {
    id: 'bn_bay',
    fixtureId: 'fx_bay',
    seatNumber: 4,
    authorId: 'u_sarah',
    postedAt: '2026-09-19T09:12:00',
    // 'repay' moves face value to whoever takes the seat; 'free' moves nothing.
    costPath: 'repay',
    amountCents: 9500,
    body: "Out of town for the Bay match — seat 4 is free if anyone wants it.",
    replies: [
      { id: 'r1', authorId: 'u_jason', at: '2026-09-19T09:40:00', body: "We'll miss you — I'll ask my sister." },
    ],
  },
];

export const quickReplies = ["I'll take them", "We'll miss you", 'Anyone else in?'];

// Simplified debts: the ledger nets the circle down to the fewest transfers.
export const ledger = {
  2026: {
    packageCents: 248000,
    paid: { u_you: 52000, u_jason: 45500, u_sarah: 50000, u_alice: 46500, u_bob: 54000 },
    owed: { u_you: 47500, u_jason: 50500, u_sarah: 49500, u_alice: 50500, u_bob: 50000 },
    debts: [
      { from: 'u_alice', to: 'u_jason', cents: 4000 },
      { from: 'u_jason', to: 'u_you', cents: 4500 },
    ],
  },
  2025: {
    packageCents: 231000,
    paid: { u_you: 46200, u_jason: 46200, u_sarah: 46200, u_alice: 46200, u_bob: 46200 },
    owed: { u_you: 46200, u_jason: 46200, u_sarah: 46200, u_alice: 46200, u_bob: 46200 },
    debts: [],
  },
};

export const settleApps = [
  { id: 'venmo',   name: 'Venmo',     link: (a, m) => `https://venmo.com/?txn=pay&amount=${a}&note=${encodeURIComponent(m)}` },
  { id: 'cashapp', name: 'Cash App',  link: (a) => `https://cash.app/$/${a}` },
  { id: 'zelle',   name: 'Zelle',     link: () => 'https://www.zellepay.com/' },
];

// ---------- Home Team (the Locker Room) ----------
export const squad = [
  { id: 'p1',  num: 1,  name: 'Rowan Vasquez',  pos: 'GK',  stats: [['Clean sheets', '7'], ['Saves', '54'], ['Starts', '19']], note: 'Comes for everything in the six. The Hearth breathes easier when she claims the first cross.' },
  { id: 'p2',  num: 4,  name: 'Imani Brooks',   pos: 'DEF', stats: [['Tackles', '48'], ['Duels won', '62%'], ['Starts', '21']], note: 'Steps in front of the pass rather than chasing it. Reads the game a beat early.' },
  { id: 'p3',  num: 5,  name: 'Freja Lindholm', pos: 'DEF', stats: [['Clearances', '71'], ['Aerials', '58%'], ['Starts', '20']], note: 'The bench captain in everything but the armband. Organises the line from kickoff.' },
  { id: 'p4',  num: 6,  name: 'Priya Raman',    pos: 'MID', stats: [['Passes', '1,204'], ['Accuracy', '88%'], ['Starts', '22']], note: 'Sets the tempo the way you bank a fire — quietly, and all night.' },
  { id: 'p5',  num: 8,  name: 'Nadia Okafor',   pos: 'MID', stats: [['Assists', '9'], ['Key passes', '41'], ['Starts', '18']], note: 'Finds the runner nobody else saw. Watch her shoulders, not the ball.' },
  { id: 'p6',  num: 10, name: 'Sloane Beckett',  pos: 'MID', stats: [['Goals', '6'], ['Assists', '11'], ['Starts', '21']], note: 'Drops off the front line to collect, then turns. The whole attack pivots on that turn.' },
  { id: 'p7',  num: 9,  name: 'Tess Aldridge',  pos: 'FWD', stats: [['Goals', '14'], ['Shots/90', '3.8'], ['Starts', '22']], note: 'Runs the channel until the centre-back blinks. Fourteen goals say the blink comes.' },
  { id: 'p8',  num: 11, name: 'Juno Park',      pos: 'FWD', stats: [['Goals', '8'], ['Dribbles', '63'], ['Starts', '17']], note: 'Takes the outside shoulder every time, and it works roughly every third time.' },
  { id: 'p9',  num: 17, name: 'Camille Duarte', pos: 'FWD', stats: [['Goals', '5'], ['Sub apps', '14'], ['Minutes', '612']], note: 'The sub who changes the temperature. Rarely starts, often decides.' },
  { id: 'p10', num: 23, name: 'Harper Nakamura', pos: 'DEF', stats: [['Interceptions', '39'], ['Crosses', '52'], ['Starts', '16']], note: 'Overlaps into the space Juno vacates. The two of them read each other well.' },
];

export const positions = ['Whole squad', 'GK', 'DEF', 'MID', 'FWD'];

// ---------- Visitors (the visiting club's dressing room) ----------
export const opponents = [
  {
    id: 'op_por', club: 'Portland Thorns', chip: 'Portland · 9/26',
    homeDate: '9/26', awayDate: '5/9', awayVenue: 'Providence Park',
    form: 'W W D L W', shape: '4-3-3, inverted right back, high line they will not drop.',
    quickStats: [['Goals for', '31'], ['Goals against', '19'], ['Away wins', '5']],
    halftime: 'They press the goal kick for twenty minutes and then stop. Play through the first twenty and the second half opens up.',
    players: [
      { id: 'o1', num: 9,  name: 'Marisol Vega',  pos: 'FWD', danger: true,  note: 'Every dangerous move starts with her drifting to the left half-space. Track it or lose the game.' },
      { id: 'o2', num: 6,  name: 'Elin Sandberg', pos: 'MID', danger: false, note: 'Screens the back four. Slow across the ground — go at her sideways, not through her.' },
      { id: 'o3', num: 2,  name: 'Dara Whitfield', pos: 'DEF', danger: false, note: 'Overlaps constantly and recovers late. The space behind her is the game.' },
    ],
  },
  {
    id: 'op_bay', club: 'Bay FC', chip: 'Bay · 10/3',
    homeDate: '10/3', awayDate: '6/20', awayVenue: 'PayPal Park',
    form: 'L D W L D', shape: '4-4-2 block, counters through the left channel.',
    quickStats: [['Goals for', '22'], ['Goals against', '26'], ['Away wins', '2']],
    halftime: 'They sit, they absorb, and they break once. Keep a body on the counter and the afternoon is comfortable.',
    players: [
      { id: 'o4', num: 11, name: 'Noor Haddad',   pos: 'FWD', danger: true,  note: 'The one who hurts you on the break. Nine of her twelve goals came inside four passes.' },
      { id: 'o5', num: 8,  name: 'Robin Castellanos', pos: 'MID', danger: false, note: 'Takes every set piece. Left foot, near post, in-swinging.' },
      { id: 'o6', num: 1,  name: 'Ada Lindgren',  pos: 'GK',  danger: false, note: 'Strong hands, hesitant feet. Press the back pass.' },
    ],
  },
  {
    id: 'op_acf', club: 'Angel City FC', chip: 'Angel City · 10/18',
    homeDate: '10/18', awayDate: '7/11', awayVenue: 'BMO Stadium',
    form: 'W W W D W', shape: '3-4-3, wing-backs high, three at the back that can be turned.',
    quickStats: [['Goals for', '36'], ['Goals against', '17'], ['Away wins', '7']],
    halftime: 'The wing-backs are still up the pitch at 60 minutes. That is when the diagonal behind them is on.',
    players: [
      { id: 'o7', num: 7,  name: 'Céline Abara',  pos: 'FWD', danger: true,  note: 'Best player on either team most weeks. Double her the moment she faces up.' },
      { id: 'o8', num: 3,  name: 'Wren Okonkwo',  pos: 'DEF', danger: false, note: 'Left of the three. Comfortable stepping in, uncomfortable turning.' },
      { id: 'o9', num: 16, name: 'Tamsin Reyes',  pos: 'MID', danger: false, note: 'Runs the whole game at one speed. Tires after 70.' },
    ],
  },
];

// ---------- Hearthside Notes ----------
export const hearthsideNotes = [
  {
    kind: 'player',
    eyebrow: 'Key player to watch',
    num: 9,
    name: 'Tess Aldridge',
    pos: 'Forward · Denver Summit FC',
    body: 'Fourteen goals in twenty-two starts, and eleven of them from inside the six. She lives on the back shoulder.',
  },
  {
    kind: 'tactics',
    eyebrow: 'Rivalry note',
    name: 'Portland hold a high line',
    body: "Portland have not dropped their line all season, and Summit have the two quickest forwards in the league. The game is decided in the twenty yards behind Dara Whitfield.",
  },
  {
    kind: 'trivia',
    eyebrow: 'Tap to reveal',
    question: 'Summit Park sits at what elevation?',
    answer: '5,280 feet — the away sign in the visiting dressing room is not decoration.',
  },
];
