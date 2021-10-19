import QtQuick 2.4
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.4
import org.kde.kirigami 2.4 as Kirigami
import QtGraphicalEffects 1.0
import Mycroft 1.0 as Mycroft

Item {
    id: root
    property alias imgSrc: img.source
    property bool rounded: true
    property bool imageModeExpanded: true

    Item {
        id: imgRoot
        width: parent.width
        height: parent.height
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom

        Image {
            id: img
            anchors.fill: parent
            opacity: 0
            fillMode: imageModeExpanded ? Image.PreserveAspectCrop : Image.PreserveAspectFit

            asynchronous: true
            onStatusChanged: {
                if (status == Image.Ready) {
                    if (sourceSize.width >= root.width) {
                        imageModeExpanded = true
                        opacity = 1
                    } else {
                        imageModeExpanded = false
                        opacity = 1
                    }
                }
            }

            layer.enabled: root.rounded ? 1 : 0
            layer.effect: OpacityMask {
                cached: true
                maskSource: Rectangle {
                    width: imgRoot.width
                    height: imgRoot.height
                    visible: false
                    radius: Mycroft.Units.gridUnit
                }
            }
        }
    }

    Mycroft.BusyIndicator {
        anchors.centerIn: parent
        running: img.status === Image.Loading || img.source == "" ? 1 : 0
        visible: running
    }
}
