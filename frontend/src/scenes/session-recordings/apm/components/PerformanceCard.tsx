import clsx from 'clsx'
import { LemonDivider } from 'lib/lemon-ui/LemonDivider'
import { Link } from 'lib/lemon-ui/Link'
import { Tooltip } from 'lib/lemon-ui/Tooltip'
import { humanFriendlyMilliseconds } from 'lib/utils'
import { Fragment } from 'react'

import { PerformanceEvent } from '~/types'

export const performanceSummaryCards = [
    {
        label: 'First Contentful Paint',
        description: (
            <div>
                The First Contentful Paint (FCP) metric measures the time from when the page starts loading to when any
                part of the page's content is rendered on the screen.{' '}
                <Link
                    disableClientSideRouting
                    to="https://developer.mozilla.org/en-US/docs/Glossary/First_contentful_paint"
                    target="_blank"
                >
                    Read more on developer.mozilla.org
                </Link>
            </div>
        ),
        key: 'first_contentful_paint',
        scoreBenchmarks: [1800, 3000],
    },
    {
        label: 'DOM Interactive',
        description: (
            <div>
                The document has finished loading and the document has been parsed but sub-resources such as scripts,
                images, stylesheets and frames are still loading.{' '}
                <Link
                    disableClientSideRouting
                    to="https://developer.mozilla.org/en-US/docs/Web/API/Document/readyState"
                    target="_blank"
                >
                    Read more on developer.mozilla.org
                </Link>
            </div>
        ),
        key: 'dom_interactive',
        scoreBenchmarks: [3800, 7300],
    },
    {
        label: 'Page Loaded',
        description: (
            <div>
                The load event is fired when the whole page has loaded, including all dependent resources such as
                stylesheets and images. This is in contrast to DOMContentLoaded, which is fired as soon as the page DOM
                has been loaded, without waiting for resources to finish loading.{' '}
                <Link
                    disableClientSideRouting
                    to="https://developer.mozilla.org/en-US/docs/Web/API/Window/load_event"
                    target="_blank"
                >
                    Read more on developer.mozilla.org
                </Link>
            </div>
        ),
        key: 'load_event_end',
        scoreBenchmarks: [3800, 7300],
    },
]

export function PerformanceDuration({
    value,
    benchmarkKey,
}: {
    benchmarkKey: string
    value: number | undefined
}): JSX.Element {
    const scoreBenchmarks = performanceSummaryCards.find(({ key }) => key === benchmarkKey)?.scoreBenchmarks ?? [
        3000, 6000,
    ]
    return value === undefined ? (
        <>-</>
    ) : (
        <span
            className={clsx({
                'text-danger-dark': value >= scoreBenchmarks[1],
                'text-warning-dark': value >= scoreBenchmarks[0] && value < scoreBenchmarks[1],
                'text-success-dark': value < scoreBenchmarks[0],
            })}
        >
            {humanFriendlyMilliseconds(value)}
        </span>
    )
}

function PerformanceCard({
    description,
    label,
    value,
    benchmarkKey,
}: {
    benchmarkKey: string
    description: JSX.Element
    label: string
    value: number | undefined
}): JSX.Element {
    return (
        <Tooltip title={description}>
            <div className="flex-1 p-2 text-center">
                <div className="text-sm">{label}</div>
                <div className="text-lg font-semibold">
                    <PerformanceDuration value={value} benchmarkKey={benchmarkKey} />
                </div>
            </div>
        </Tooltip>
    )
}

export function PerformanceCardRow({
    item,
    title,
}: {
    item: PerformanceEvent
    title: JSX.Element | null
}): JSX.Element {
    return (
        <div className="flex flex-col space-y-2">
            {title}
            <div className="flex items-center p-2">
                {performanceSummaryCards.map(({ label, description, key }, index) => (
                    <Fragment key={key}>
                        {index !== 0 && <LemonDivider vertical dashed />}
                        <PerformanceCard label={label} description={description} value={item[key]} benchmarkKey={key} />
                    </Fragment>
                ))}
            </div>
        </div>
    )
}

export function PerformanceCardDescriptions({
    item,
    expanded,
}: {
    item: PerformanceEvent
    expanded: boolean
}): JSX.Element {
    return (
        <div className={clsx('p-2 text-xs border-t', !expanded && 'hidden')}>
            {performanceSummaryCards.map(({ label, description, key }) => (
                <div key={key}>
                    <div className="flex gap-2 font-semibold my-1">
                        <span>{label}</span>
                        <PerformanceDuration benchmarkKey={key} value={item?.[key]} />
                    </div>

                    <p>{description}</p>
                </div>
            ))}
        </div>
    )
}
