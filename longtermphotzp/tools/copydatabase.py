'''
Tool to copy gain history data from one database to another, in particular to support hte migration from local sqlite to online postgress.
'''
import argparse
import logging
import itertools
from longtermphotzp.photdbinterface import photdbinterface, PhotZPMeasurement
import datetime

def parseCommandLine():
    parser = argparse.ArgumentParser(
        description='Copy noisegain database from A to B')

    parser.add_argument('--loglevel', dest='log_level', default='INFO', choices=['DEBUG', 'INFO', 'WARN'],
                        help='Set the debug level')

    parser.add_argument('--inputurl', type=str, default='sqlite:///lcophotzp.db', help="input database")
    parser.add_argument('--outputurl', type=str, default='sqlite:///testout.db', help="input database")

    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()),
                        format='%(asctime)s.%(msecs).03d %(levelname)7s: %(module)20s: %(message)s')
    return args

def divide_chunks(l, n):

    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]

if __name__ == '__main__':
    args = parseCommandLine()
    start = 435
    print(f"Copy from {args.inputurl} -> {args.outputurl}")

    input = photdbinterface(args.inputurl)
    output = photdbinterface(args.outputurl)

    q = input.session.query(PhotZPMeasurement)
    print("Found {} records to copy.".format(q.count()))
    newdata = [PhotZPMeasurement(e) for e in q.all()]

    print("Now doing bulk insert in chunks")

    chunks = list(divide_chunks(newdata, 1000))
    print (f'Divided data ino {len(chunks)} chunks')
    for ii in range (start, len(chunks)):
        print (f'Start write chunk {ii} at {datetime.datetime.utcnow()}')
        output.session.bulk_save_objects(chunks[ii])
        output.session.commit()
        print (f'Done write chunk {ii} at {datetime.datetime.utcnow()}')



    input.close()
    output.close()
