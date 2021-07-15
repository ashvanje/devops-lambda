require('./setup')

const { readdirSync } = require('fs')
const { resolve } = require('path')
const Event = require('./lib/Event')

/**
 * Load the pipeline files.
 */

const pipelineDir = 'pipeline'
const pipelineFiles = readdirSync(pipelineDir)
  .filter((f) => f.endsWith('.js'))
  .sort()
const transforms = pipelineFiles.map((f) => {
  console.info(`Loading pipeline file: ${f}`)
  return require(resolve(__dirname, pipelineDir, f))
})

/**
 * Generate the next callback.
 */
function getNext(i, done) {
  if (i < pipelineFiles.length) {
    return (err, event) => {
      if (err) {
        done(err)
        return
      }

      if (!event) {
        console.debug('The event is dropped')
        done()
        return
      }

      console.debug(`Transforming: ${pipelineFiles[i]}`)
      if (logLevel.trace) {
        console.trace(`Transforming: ${pipelineFiles[i]}: ${event.toString()}`)
      }

      try {
        transforms[i](event, getNext(i + 1, done))
      } catch (err) {
        done(err)
      }
    }
  }
  return (err) => done(err)
}

/**
 * Handle the incoming payload.
 */

exports.handler = function(payload, ctx, done) {
  console.info('Received new payload')
  if (logLevel.trace) {
    console.trace('Received new payload: %j', payload)
  }

  if (!payload) {
    done(new Error('Received empty payload'))
    return
  }

  let event = new Event(payload)
  getNext(0, done)(null, event)
}
