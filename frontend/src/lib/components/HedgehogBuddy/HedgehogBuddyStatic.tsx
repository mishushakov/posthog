import { COLOR_TO_FILTER_MAP, HedgehogColorOptions } from './hedgehogBuddyLogic'
import { baseSpriteAccessoriesPath, baseSpritePath, standardAccessories } from './sprites/sprites'

export type HedgehogBuddyStaticProps = {
    size?: number
    accessories?: string[]
    color?: HedgehogColorOptions | null
}

// Takes a range of options and renders a static hedgehog
export function HedgehogBuddyStatic({ accessories, color }: HedgehogBuddyStaticProps): JSX.Element {
    const imgSize = 60
    const hedgehogImgSize = imgSize * 4

    const accessoryInfos = accessories?.map((x) => standardAccessories[x])
    const filter = color ? COLOR_TO_FILTER_MAP[color] : null

    return (
        <div
            className="relative overflow-hidden pointer-events-none"
            // eslint-disable-next-line react/forbid-dom-props
            style={{
                width: imgSize,
                height: imgSize,
                margin: -2,
            }}
        >
            <img
                src={`${baseSpritePath()}/wave.png`}
                className="object-cover absolute inset-0 image-pixelated"
                // eslint-disable-next-line react/forbid-dom-props
                style={{
                    width: hedgehogImgSize,
                    height: hedgehogImgSize,
                    filter: filter as any,
                }}
            />

            {accessoryInfos?.map((accessory, index) => (
                <img
                    key={index}
                    src={`${baseSpriteAccessoriesPath()}/${accessory.img}.png`}
                    className="object-cover absolute inset-0 image-pixelated"
                    // eslint-disable-next-line react/forbid-dom-props
                    style={{
                        width: imgSize,
                        height: imgSize,
                        filter: filter as any,
                    }}
                />
            ))}
        </div>
    )
}
