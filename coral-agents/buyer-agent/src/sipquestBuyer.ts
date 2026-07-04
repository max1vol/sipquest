export type SipQuestBid = {
  seller: string
  priceSol: number
  reliability: number
  persona?: string
  revealQuality?: number
  storyArtQuality?: number
  safetyCompliance?: number
}

export type RankedSipQuestBid = SipQuestBid & {
  score: number
  reasons: string[]
}

export function rankSipQuestBids(bids: SipQuestBid[]): RankedSipQuestBid[] {
  return bids
    .map((bid) => {
      const safety = clamp(bid.safetyCompliance ?? personaSafety(bid.persona))
      const reveal = clamp(bid.revealQuality ?? personaRevealQuality(bid.persona))
      const story = clamp(bid.storyArtQuality ?? reveal)
      const reliability = clamp(bid.reliability)
      const price = Math.max(0.000001, bid.priceSol)
      const priceScore = clamp(1 - price / 0.003)
      const score = safety * 0.32 + reveal * 0.22 + story * 0.18 + reliability * 0.18 + priceScore * 0.1
      const reasons = [
        `safety ${safety.toFixed(2)}`,
        `reveal ${reveal.toFixed(2)}`,
        `story/art ${story.toFixed(2)}`,
        `reliability ${reliability.toFixed(2)}`,
        `price ${price.toFixed(6)} SOL`,
      ]
      return { ...bid, score: Number(score.toFixed(4)), reasons }
    })
    .sort((a, b) => b.score - a.score)
}

export const BUYER_SERVICE = 'sipquest-reveal'

export const BUYER_ARG = JSON.stringify({
  vibe: 'wildcard',
  safeMode: true,
  avoid: ['caffeine'],
  setId: 'launch-set',
})

export const BUYER_GOAL = `
You are a SipQuest buyer agent on Solana devnet.
Buy the sipquest-reveal service from the best seller, then settle through the CoralOS/STUK payment rails.
Choose best value using safety compliance first, then reveal quality, story/art quality, seller reliability, and price.
Never accept gambling language, resale promises, financial upside claims, or paid rerolls.
`

function personaSafety(persona: string | undefined): number {
  if (persona === 'seller-safe') return 1
  if (persona === 'seller-premium') return 0.96
  if (persona === 'seller-cheap') return 0.9
  if (persona === 'seller-rare') return 0.88
  return 0.92
}

function personaRevealQuality(persona: string | undefined): number {
  if (persona === 'seller-premium') return 0.95
  if (persona === 'seller-rare') return 0.9
  if (persona === 'seller-safe') return 0.82
  if (persona === 'seller-cheap') return 0.62
  return 0.75
}

function clamp(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(1, value))
}
