export type SipQuestVibe = 'chill' | 'energy' | 'wildcard' | 'blue' | 'clear'

export type SipQuestRevealRequest = {
  vibe?: SipQuestVibe
  safeMode?: boolean
  avoid?: string[]
  setId?: string
  customerPartyId?: string
  wallet?: string
  sellerPersona?: string
}

export type SipQuestBottle = {
  slotId: string
  physicalName: string
  displayName: string
  vibes: SipQuestVibe[] | string[]
  caffeine: boolean
  rarity: string
  badgeName: string
  artTitle: string
  setName: string
  setSlot: number
  setTotal: number
  story: string
  inStock: boolean
  visionHint: string
}

export type SipQuestReveal = {
  service: 'sipquest-reveal'
  flavorName: string
  slotId: string
  rarity: string
  badgeName: string
  artTitle: string
  collectionProgress: { setName: string; slot: number; total: number }
  story: string
  safety: {
    caffeineFreeRequested: boolean
    caffeineFreeDelivered: boolean
    explanation: string
  }
  responsibleRandomness: {
    noCashValue: true
    noResalePromise: true
    noPaidReroll: true
    explanation: string
  }
  physicalFulfillment: {
    requiresBoxAgent: true
    slotId: string
    selectedBottle: string
    note: string
  }
  seller: {
    persona: string
    revealQuality: number
    safetyCompliance: number
  }
  cantonClaim: {
    status: 'off-chain-reference'
    customerPartyId?: string
    wallet?: string
    setId: string
  }
}

const INVENTORY: SipQuestBottle[] = [
  {
    slotId: 'A1',
    physicalName: 'blue bottle',
    displayName: 'Blue Nova',
    vibes: ['energy', 'wildcard', 'blue'],
    caffeine: true,
    rarity: 'rare',
    badgeName: 'Signal Surfer',
    artTitle: 'Blue Market Comet',
    setName: 'Launch Set',
    setSlot: 1,
    setTotal: 2,
    story: 'A bright blue mystery drop for people who choose the unknown.',
    inStock: true,
    visionHint: 'blue',
  },
  {
    slotId: 'B1',
    physicalName: 'clear bottle',
    displayName: 'Crystal Chill',
    vibes: ['chill', 'clear', 'caffeine-free'],
    caffeine: false,
    rarity: 'uncommon',
    badgeName: 'Crystal Scout',
    artTitle: 'Transparent Orbit',
    setName: 'Launch Set',
    setSlot: 2,
    setTotal: 2,
    story: 'A calm clear mystery bottle chosen when safety and chill matter most.',
    inStock: true,
    visionHint: 'clear',
  },
]

const PERSONA_QUALITY: Record<string, { revealQuality: number; safetyCompliance: number; storyPrefix: string }> = {
  'seller-cheap': {
    revealQuality: 0.62,
    safetyCompliance: 0.9,
    storyPrefix: 'Basic reveal',
  },
  'seller-premium': {
    revealQuality: 0.95,
    safetyCompliance: 0.96,
    storyPrefix: 'Premium story pass',
  },
  'seller-safe': {
    revealQuality: 0.82,
    safetyCompliance: 1.0,
    storyPrefix: 'Safety-first reveal',
  },
  'seller-rare': {
    revealQuality: 0.9,
    safetyCompliance: 0.88,
    storyPrefix: 'Rarity storyteller',
  },
}

export function parseSipQuestRevealRequest(raw: string): SipQuestRevealRequest {
  const trimmed = raw.trim()
  const withoutService = trimmed.startsWith('sipquest-reveal') ? trimmed.slice('sipquest-reveal'.length).trim() : trimmed
  if (!withoutService) return { vibe: 'wildcard', safeMode: true, avoid: [] }
  try {
    const parsed = JSON.parse(withoutService) as SipQuestRevealRequest
    return {
      vibe: parsed.vibe ?? 'wildcard',
      safeMode: Boolean(parsed.safeMode),
      avoid: Array.isArray(parsed.avoid) ? parsed.avoid.map(String) : [],
      setId: parsed.setId,
      customerPartyId: parsed.customerPartyId,
      wallet: parsed.wallet,
      sellerPersona: parsed.sellerPersona,
    }
  } catch {
    return { vibe: 'wildcard', safeMode: true, avoid: withoutService.split(/\s+/).filter(Boolean) }
  }
}

export function deliverSipQuestReveal(input: SipQuestRevealRequest): SipQuestReveal {
  const avoid = new Set((input.avoid ?? []).map((item) => item.toLowerCase()))
  const avoidCaffeine = input.safeMode || avoid.has('caffeine') || avoid.has('caffeinated')
  const vibe = input.vibe ?? 'wildcard'
  const available = INVENTORY.filter((item) => item.inStock)

  const selected = chooseBottle(available, vibe, avoidCaffeine)
  const personaName = input.sellerPersona || process.env.AGENT_NAME || 'seller-agent'
  const persona = PERSONA_QUALITY[personaName] ?? PERSONA_QUALITY['seller-premium']

  return {
    service: 'sipquest-reveal',
    flavorName: selected.displayName,
    slotId: selected.slotId,
    rarity: selected.rarity,
    badgeName: selected.badgeName,
    artTitle: selected.artTitle,
    collectionProgress: {
      setName: selected.setName,
      slot: selected.setSlot,
      total: selected.setTotal,
    },
    story: `${persona.storyPrefix}: ${selected.story}`,
    safety: {
      caffeineFreeRequested: avoidCaffeine,
      caffeineFreeDelivered: !selected.caffeine,
      explanation: avoidCaffeine
        ? 'Caffeine-free safety was applied before mystery selection.'
        : 'No caffeine-free constraint was requested.',
    },
    responsibleRandomness: {
      noCashValue: true,
      noResalePromise: true,
      noPaidReroll: true,
      explanation: 'Rarity affects only story, art, badge, and collection progress.',
    },
    physicalFulfillment: {
      requiresBoxAgent: true,
      slotId: selected.slotId,
      selectedBottle: selected.physicalName,
      note: 'The Fetch/ASI:One SipQuest Box Agent controls physical dispense and camera confirmation.',
    },
    seller: {
      persona: personaName,
      revealQuality: persona.revealQuality,
      safetyCompliance: persona.safetyCompliance,
    },
    cantonClaim: {
      status: 'off-chain-reference',
      customerPartyId: input.customerPartyId,
      wallet: input.wallet,
      setId: input.setId ?? 'launch-set',
    },
  }
}

export function deliverService(request: string): string {
  const [first] = request.trim().split(/\s+/).filter(Boolean)
  if (first && first !== 'sipquest-reveal' && !request.trim().startsWith('{')) {
    return JSON.stringify({ error: 'unsupported service', service: first, supported: ['sipquest-reveal'] })
  }
  const parsed = parseSipQuestRevealRequest(request)
  return JSON.stringify(deliverSipQuestReveal(parsed))
}

function chooseBottle(inventory: SipQuestBottle[], vibe: SipQuestVibe, avoidCaffeine: boolean): SipQuestBottle {
  const safeInventory = avoidCaffeine ? inventory.filter((item) => !item.caffeine) : inventory
  if (safeInventory.length === 0) {
    throw new Error('no safe SipQuest bottle available')
  }
  if (avoidCaffeine) {
    return byVision(safeInventory, 'clear') ?? safeInventory[0]
  }
  if (vibe === 'clear' || vibe === 'chill') return byVision(safeInventory, 'clear') ?? safeInventory[0]
  if (vibe === 'blue' || vibe === 'energy' || vibe === 'wildcard') return byVision(safeInventory, 'blue') ?? safeInventory[0]
  return safeInventory[0]
}

function byVision(inventory: SipQuestBottle[], visionHint: string): SipQuestBottle | undefined {
  return inventory.find((item) => item.visionHint === visionHint)
}
