from Data.Download import Download
import asyncio

def main():

    Download.start()
    asyncio.run(Download.realtime())


if __name__ == "__main__":

    main()