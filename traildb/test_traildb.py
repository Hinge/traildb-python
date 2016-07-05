import os
import uuid
import unittest
import datetime

from traildb import TrailDB, TrailDBConstructor, tdb_item_field, tdb_item_val
from traildb import TrailDBError, TrailDBCursor


class TestAPI(unittest.TestCase):

    def setUp(self):
        self.uuid = uuid.uuid4().hex[:16]
        cons = TrailDBConstructor('testtrail', ['field1', 'field2'])
        cons.add(self.uuid, 1, ['a', '1'])
        cons.add(self.uuid, 2, ['b', '2'])
        cons.add(self.uuid, 3, ['c', '3'])
        cons.finalize()

    def tearDown(self):
        os.unlink('testtrail.tdb')

    def test_trails(self):
        db = TrailDB(b'testtrail')
        self.assertEqual(db.num_trails, 1)

        trail = db.trail(0)
        self.assertIsInstance(trail, TrailDBCursor)

        # Force evaluation of generator
        events = list(trail)
        self.assertEqual(len(events), 3)
        for event in events:
            self.assertTrue(hasattr(event, 'time'))
            self.assertTrue(hasattr(event, 'field1'))
            self.assertTrue(hasattr(event, 'field2'))

    def test_crumbs(self):
        db = TrailDB(b'testtrail.tdb')

        n = 0
        for uuid, trail in db.trails():
            n += 1
            self.assertEqual(self.uuid.encode(), uuid)
            self.assertIsInstance(trail, TrailDBCursor)
            self.assertEqual(3, len(list(trail)))

        self.assertEqual(1, n)

    def test_silly_open(self):
        self.assertTrue(os.path.exists('testtrail.tdb'))
        self.assertFalse(os.path.exists('testtrail'))

        TrailDB(b'testtrail.tdb')
        TrailDB(b'testtrail')

        with self.assertRaises(TrailDBError):
            TrailDB(b'foo.tdb')

    def test_fields(self):
        db = TrailDB(b'testtrail')
        self.assertEqual(['time', 'field1', 'field2'], db.fields)

    def test_uuids(self):
        db = TrailDB(b'testtrail')
        self.assertEqual(0, db.get_trail_id(self.uuid))
        self.assertEqual(self.uuid.encode(), db.get_uuid(0))
        self.assertTrue(self.uuid in db)

    def test_lexicons(self):
        db = TrailDB(b'testtrail')

        # First field
        self.assertEqual(4, db.lexicon_size(1))
        self.assertEqual([b'a', b'b', b'c'], list(db.lexicon(1)))

        # Second field
        self.assertEqual([b'1', b'2', b'3'], list(db.lexicon(2)))

        with self.assertRaises(TrailDBError):
            # Out of bounds
            db.lexicon(3)

    def test_metadata(self):
        db = TrailDB(b'testtrail.tdb')
        self.assertEqual(1, db.min_timestamp())
        self.assertEqual(3, db.max_timestamp())
        self.assertEqual((1, 3), db.time_range())

        self.assertEqual((1, 3), db.time_range(parsetime=False))


class TestCons(unittest.TestCase):

    def setUp(self):
        self.uuid = uuid.uuid4().hex[:16]

    def test_cursor(self):
        cons = TrailDBConstructor('testtrail', ['field1', 'field2'])
        cons.add(self.uuid, 1, ['a', '1'])
        cons.add(self.uuid, 2, ['b', '2'])
        cons.add(self.uuid, 3, ['c', '3'])
        cons.add(self.uuid, 4, ['d', '4'])
        cons.add(self.uuid, 5, ['e', '5'])
        tdb = cons.finalize()

        with self.assertRaises(IndexError):
            tdb.get_trail_id('12345678123456781234567812345679')

        trail = tdb.trail(tdb.get_trail_id(self.uuid))
        with self.assertRaises(TypeError):
            len(trail)

        j = 1
        for event in trail:
            self.assertEqual(j, int(event.field2))
            self.assertEqual(j, int(event.time))
            j += 1
        self.assertEqual(6, j)

        # Iterator is empty now
        self.assertEqual([], list(trail))

        field1_values = [e.field1 for e in tdb.trail(tdb.get_trail_id(self.uuid))]
        self.assertEqual(field1_values, [b'a', b'b', b'c', b'd', b'e'])

    def test_cursor_parsetime(self):
        cons = TrailDBConstructor('testtrail', ['field1'])

        events = [(datetime.datetime(2016, 1, 1, 1, 1), ['1']),
                  (datetime.datetime(2016, 1, 1, 1, 2), ['2']),
                  (datetime.datetime(2016, 1, 1, 1, 3), ['3'])]
        [cons.add(self.uuid, time, fields) for time, fields in events]
        tdb = cons.finalize()

        timestamps = [e.time for e in tdb.trail(0, parsetime=True)]

        self.assertIsInstance(timestamps[0], datetime.datetime)
        self.assertEqual([time for time, _ in events], timestamps)
        self.assertEquals(tdb.time_range(True),
                          (events[0][0], events[-1][0]))

    def test_binarydata(self):
        binary = '\x00\x01\x02\x00\xff\x00\xff'
        cons = TrailDBConstructor('testtrail', ['field1'])
        cons.add(self.uuid, 123, [binary])
        tdb = cons.finalize()
        self.assertEqual(list(tdb[0])[0].field1, binary.encode())

    def test_cons(self):
        cons = TrailDBConstructor('testtrail', ['field1', 'field2'])
        cons.add(self.uuid, 123, ['a'])
        cons.add(self.uuid, 124, ['b', 'c'])
        tdb = cons.finalize()

        self.assertEqual(0, tdb.get_trail_id(self.uuid))
        self.assertEqual(tdb.get_uuid(0), self.uuid.encode())
        self.assertEqual(1, tdb.num_trails)
        self.assertEqual(2, tdb.num_events)
        self.assertEqual(3, tdb.num_fields)

        crumbs = list(tdb.trails())
        self.assertEqual(1, len(crumbs))
        self.assertEqual(crumbs[0][0], self.uuid.encode())
        self.assertTrue(tdb[self.uuid])
        self.assertTrue(self.uuid in tdb)
        self.assertFalse('00000000000000000000000000000000' in tdb)
        with self.assertRaises(IndexError):
            tdb['00000000000000000000000000000000']

        trail = list(crumbs[0][1])

        self.assertEqual(trail[0].time, 123)
        self.assertEqual(trail[0].field1, b'a')
        self.assertEqual(trail[0].field2, b'')

        self.assertEqual(trail[1].time, 124)
        self.assertEqual(trail[1].field1, b'b')
        self.assertEqual(trail[1].field2, b'c')

    def test_items(self):
        cons = TrailDBConstructor('testtrail', ['field1', 'field2'])
        cons.add(self.uuid, 123, ['a', 'x' * 2048])
        cons.add(self.uuid, 124, ['b', 'y' * 2048])
        tdb = cons.finalize()

        cursor = tdb.trail(0, rawitems=True)
        event = cursor.next()
        self.assertEqual(b'a', tdb.get_item_value(event.field1))
        self.assertEqual(b'x' * 2048, tdb.get_item_value(event.field2))
        self.assertEqual(event.field1, tdb.get_item('field1', b'a'))
        self.assertEqual(event.field2, tdb.get_item('field2', b'x' * 2048))
        event = cursor.next()
        self.assertEqual(b'b', tdb.get_item_value(event.field1))
        self.assertEqual(b'y' * 2048, tdb.get_item_value(event.field2))
        self.assertEqual(event.field1, tdb.get_item('field1', b'b'))
        self.assertEqual(event.field2, tdb.get_item('field2', b'y' * 2048))

        cursor = tdb.trail(0, rawitems=True)
        event = cursor.next()
        field = tdb_item_field(event.field1)
        val = tdb_item_val(event.field1)
        self.assertEqual(b'a', tdb.get_value(field, val))
        field = tdb_item_field(event.field2)
        val = tdb_item_val(event.field2)
        self.assertEqual(b'x' * 2048, tdb.get_value(field, val))
        event = cursor.next()
        field = tdb_item_field(event.field1)
        val = tdb_item_val(event.field1)
        self.assertEqual(b'b', tdb.get_value(field, val))
        field = tdb_item_field(event.field2)
        val = tdb_item_val(event.field2)
        self.assertEqual(b'y' * 2048, tdb.get_value(field, val))

    def test_append(self):
        cons = TrailDBConstructor('testtrail', ['field1'])
        cons.add(self.uuid, 123, ['foobarbaz'])
        tdb = cons.finalize()

        cons = TrailDBConstructor('testtrail2', ['field1'])
        cons.add(self.uuid, 124, ['barquuxmoo'])
        cons.append(tdb)
        tdb = cons.finalize()

        self.assertEqual(2, tdb.num_events)
        uuid, trail = list(tdb.trails())[0]
        trail = list(trail)
        self.assertEqual([123, 124], [e.time for e in trail])
        self.assertEqual([b'foobarbaz', b'barquuxmoo'], [e.field1 for e in trail])

    def tearDown(self):
        try:
            os.unlink('testtrail.tdb')
            os.unlink('testtrail2.tdb')
        except:
            pass


if __name__ == '__main__':
    unittest.main()
