from collections import defaultdict
import contextlib
import mock
import pytest
import sys

from yelp_kafka.error import OffsetCommitError

from yelp_kafka_tool.kafka_consumer_manager. \
    commands.offset_set import OffsetSet


class TestOffsetTest(object):

    def test_topics_dict(self):
        offset_update_tuple = "topic1.23=1000"
        expected_topics_dict = {
            "topic1": {23: 1000},
        }
        OffsetSet.topics_dict(offset_update_tuple)
        assert OffsetSet.new_offsets_dict == expected_topics_dict

    def test_topics_dict_topic_with_period(self):
        OffsetSet.new_offsets_dict = defaultdict(dict)
        offset_update_tuple = "scribe.sfo2.ranger.12=200"
        expected_topics_dict = {
            "scribe.sfo2.ranger": {12: 200},
        }
        OffsetSet.topics_dict(offset_update_tuple)
        assert OffsetSet.new_offsets_dict == expected_topics_dict

    def test_topics_dict_invalid_input(self):
        offset_update_tuple = "topic1.23.1000"
        with mock.patch.object(sys, "exit", autospec=True) as mock_exit:
            OffsetSet.topics_dict(offset_update_tuple)
            mock_exit.assert_called_once_with(1)

        offset_update_tuple = "topic1.garbage=garbage"
        with mock.patch.object(sys, "exit", autospec=True) as mock_exit:
            OffsetSet.topics_dict(offset_update_tuple)
            mock_exit.assert_called_once_with(1)

    @mock.patch(
        'yelp_kafka_tool.kafka_consumer_manager.'
        'commands.offset_set.KafkaClient',
        autospec=True,
    )
    def test_run(self, mock_client):
        OffsetSet.new_offsets_dict = {
            "topic1": {
                0: 1000,
                1: 2000,
                2: 3000,
            },
            "topic2": {
                0: 100,
                1: 200,
            },
        }

        with contextlib.nested(
            mock.patch.object(
                OffsetSet,
                'get_topics_from_consumer_group_id',
                spec=OffsetSet.get_topics_from_consumer_group_id,
            ),
            mock.patch(
                "yelp_kafka_tool.kafka_consumer_manager."
                "commands.offset_set.set_consumer_offsets",
                return_value=[],
                autospec=True
            ),
        ) as (mock_get_topics, mock_set_offsets):
            args = mock.Mock(
                groupid="some_group",
                topic=None,
                partitions=None
            )
            cluster_config = mock.Mock()
            OffsetSet.run(args, cluster_config)

            mock_client.return_value.load_metadata_for_topics. \
                assert_called_once_with()
            mock_client.return_value.close.assert_called_once_with()
            ordered_args, _ = mock_set_offsets.call_args
            assert ordered_args[1] == args.groupid
            assert ordered_args[2] == OffsetSet.new_offsets_dict

    @mock.patch(
        'yelp_kafka_tool.kafka_consumer_manager.'
        'commands.offset_set.KafkaClient',
        autospec=True,
    )
    def test_run_error_committing_offsets(self, mock_client):
        OffsetSet.new_offsets_dict = {
            "topic1": {
                0: 1000,
                1: 2000,
            },
            "topic2": {
                0: 100,
            },
        }

        with contextlib.nested(
            mock.patch.object(
                OffsetSet,
                'get_topics_from_consumer_group_id',
                spec=OffsetSet.get_topics_from_consumer_group_id,
            ),
            mock.patch(
                "yelp_kafka_tool.kafka_consumer_manager."
                "commands.offset_set.set_consumer_offsets",
                return_value=[
                    OffsetCommitError("topic1", 1, "my_error 1"),
                    OffsetCommitError("topic2", 0, "my_error 2"),
                ],
                autospec=True
            ),
            mock.patch.object(sys, "exit", autospec=True),
        ) as (mock_get_topics, mock_set_offsets, mock_exit):
            args = mock.Mock(
                groupid="some_group",
                topic=None,
                partitions=None
            )
            cluster_config = mock.Mock()
            OffsetSet.run(args, cluster_config)

            mock_client.return_value.load_metadata_for_topics. \
                assert_called_once_with()
            mock_client.return_value.close.assert_called_once_with()
            ordered_args, _ = mock_set_offsets.call_args
            assert ordered_args[1] == args.groupid
            assert ordered_args[2] == OffsetSet.new_offsets_dict
            mock_exit.assert_called_with(1)

    @mock.patch(
        'yelp_kafka_tool.kafka_consumer_manager.'
        'commands.offset_set.KafkaClient',
        autospec=True,
    )
    def test_run_bad_topics_dict(self, mock_client):
        OffsetSet.new_offsets_dict = {
            "topic1": 23,
            "topic2": 32,
        }
        with mock.patch.object(
            OffsetSet,
            'get_topics_from_consumer_group_id',
            spec=OffsetSet.get_topics_from_consumer_group_id,
        ):
            args = mock.Mock(
                groupid="some_group",
                topic=None,
                partitions=None
            )
            cluster_config = mock.Mock()
            with pytest.raises(TypeError):
                OffsetSet.run(args, cluster_config)